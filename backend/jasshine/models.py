"""MongoDB documents and database connection for JASSHINE."""
from copy import deepcopy
from datetime import datetime
import os

from flask import abort, g, has_app_context
from mongoengine import (
    BooleanField,
    DateTimeField,
    DecimalField,
    Document,
    IntField,
    QuerySet,
    QuerySetManager,
    Q,
    StringField,
    connect,
    disconnect,
    get_db,
)
from pymongo import ReturnDocument

ROLES = ("admin", "empleado", "cliente")
ROL_LABEL = {"admin": "Administrador", "empleado": "Empleado", "cliente": "Cliente"}
COMISION_PCT = 0.18


class MongoQuerySet(QuerySet):
    def filter(self, *q_objs, **query):
        if len(q_objs) > 1:
            combined = q_objs[0]
            for expression in q_objs[1:]:
                combined &= expression
            q_objs = (combined,)
        return super().filter(*q_objs, **query)

    def filter_by(self, **query):
        return self.filter(**query)

    def one(self):
        return self.get()

    def get(self, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            return super().get(pk=args[0])
        return super().get(*args, **kwargs)


class MongoSession:
    """Request-scoped unit of work for existing multi-document form flows."""

    def __init__(self):
        self._tracked = {}
        self._identity = {}

    def track(self, document):
        key = id(document)
        if document.pk is not None:
            identity_key = (document._get_collection_name(), document.pk)
            existing = self._identity.get(identity_key)
            if existing is not None and existing is not document:
                for field_name in document._fields:
                    document._data[field_name] = deepcopy(existing._data[field_name])
            else:
                self._identity[identity_key] = document
        if key not in self._tracked:
            self._tracked[key] = (document, deepcopy(document.to_mongo()))

    def add(self, document):
        self.track(document)
        document.save()
        self._tracked[id(document)] = (document, deepcopy(document.to_mongo()))
        if document.pk is not None:
            self._identity[(document._get_collection_name(), document.pk)] = document

    def delete(self, document):
        if document.pk is not None:
            document.delete()
        self._tracked.pop(id(document), None)
        self._identity.pop((document._get_collection_name(), document.pk), None)

    def get(self, model, identifier):
        return model.objects(pk=identifier).first()

    def flush(self):
        for key, (document, original) in tuple(self._tracked.items()):
            if document.pk is not None and document.to_mongo() != original:
                document.save()
                self._tracked[key] = (document, deepcopy(document.to_mongo()))

    def commit(self):
        self.flush()
        self.clear()

    def rollback(self):
        for document, _ in tuple(self._tracked.values()):
            if document.pk is not None:
                document.reload()
        self._tracked.clear()

    def clear(self):
        self._tracked.clear()
        self._identity.clear()

    remove = rollback


class MongoDatabase:
    def __init__(self):
        self._session = MongoSession()
        self._models = []
        self._connection = None
        self._database = None

    @property
    def session(self):
        if not has_app_context():
            return self._session
        if "jasshine_mongo_session" not in g:
            g.jasshine_mongo_session = MongoSession()
        return g.jasshine_mongo_session

    def register(self, model):
        self._models.append(model)
        return model

    def init_app(self, app):
        uri = app.config.get("MONGODB_URI") or os.environ.get("MONGODB_URI")
        if not uri:
            raise RuntimeError(
                "Falta MONGODB_URI. Configura la URI de MongoDB Atlas como variable de entorno."
            )
        disconnect(alias="default")
        options = {
            "db": app.config.get("MONGODB_DB") or os.environ.get("MONGODB_DB") or "jasshine",
            "host": uri,
            "alias": "default",
            "connect": False,
            "uuidRepresentation": "standard",
        }
        if app.config.get("MONGODB_MOCK"):
            from mongomock import MongoClient as MockMongoClient
            options["mongo_client_class"] = MockMongoClient
        self._connection = connect(**options)
        self._database = get_db(alias="default")
        app.extensions["mongodb"] = self._connection

    def create_all(self):
        for model in self._models:
            model.ensure_indexes()

    def drop_all(self):
        database = self._database
        if database is None:
            return
        for model in self._models:
            database.drop_collection(model._get_collection_name())
        database.drop_collection("_counters")

    def close(self):
        disconnect(alias="default")
        self._connection = None
        self._database = None

    def next_id(self, collection):
        counter = self._database.get_collection("_counters").find_one_and_update(
            {"_id": collection},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return counter["value"]

    @staticmethod
    def get_or_404(model, identifier):
        document = model.objects(pk=identifier).first()
        if document is None:
            abort(404)
        return document


db = MongoDatabase()


class MongoDocument(Document):
    meta = {"abstract": True, "queryset_class": MongoQuerySet}
    query = QuerySetManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db.session.track(self)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.pk = db.next_id(self._get_collection_name())
        result = super().save(*args, **kwargs)
        db.session.track(self)
        return result


class Usuario(MongoDocument):
    meta = {"collection": "usuarios"}
    id_usuario = IntField(primary_key=True)
    nombre = StringField(required=True, max_length=100)
    email = StringField(required=True, unique=True, max_length=150)
    contrasena = StringField(required=True, default="", max_length=255)
    rol = StringField(required=True, choices=ROLES)
    estado = StringField(required=True, default="activo", choices=("activo", "inactivo", "suspendida"))

    @property
    def id(self):
        return self.id_usuario

    @property
    def cliente(self):
        return Cliente.objects(id_usuario=self.id_usuario).first()

    @property
    def empleado(self):
        return Empleado.objects(id_usuario=self.id_usuario).first()

    @property
    def primer_nombre(self):
        partes = self.nombre.split()
        return partes[0] if partes else self.nombre

    @property
    def rol_label(self):
        return ROL_LABEL.get(self.rol, self.rol)


class Cliente(MongoDocument):
    meta = {"collection": "clientes"}
    id_cliente = IntField(primary_key=True)
    id_usuario = IntField(required=True, unique=True)
    nombre = StringField(required=True, max_length=100)
    email = StringField(required=True, max_length=150)
    telefono = StringField(max_length=20)

    @property
    def id(self):
        return self.id_cliente

    @property
    def usuario(self):
        return Usuario.objects(pk=self.id_usuario).first()

    @property
    def vehiculos(self):
        return list(Vehiculo.objects(id_cliente=self.id_cliente).order_by("id_vehiculo"))

    @property
    def reservas(self):
        return list(Reserva.objects(id_cliente=self.id_cliente))


class Vehiculo(MongoDocument):
    meta = {"collection": "vehiculos"}
    id_vehiculo = IntField(primary_key=True)
    id_cliente = IntField(required=True)
    tipo = StringField(required=True, default="Moto", max_length=50)
    placa = StringField(required=True, unique=True, max_length=20)

    @property
    def cliente(self):
        return Cliente.objects(pk=self.id_cliente).first()


class Empleado(MongoDocument):
    meta = {"collection": "empleados"}
    id_empleado = IntField(primary_key=True)
    id_usuario = IntField(required=True, unique=True)
    nombre = StringField(required=True, max_length=100)
    email = StringField(required=True, max_length=150)
    telefono = StringField(max_length=20)
    especialidad = StringField(max_length=100)
    estado = StringField(required=True, default="Disponible", max_length=30)

    @property
    def id(self):
        return self.id_empleado

    @property
    def usuario(self):
        return Usuario.objects(pk=self.id_usuario).first()

    @property
    def cargo(self):
        return self.especialidad or "Lavador"

    @property
    def en_operacion(self):
        return self.estado in ("Disponible", "En servicio")


class TipoServicio(MongoDocument):
    meta = {"collection": "tipos_servicio"}
    id_tipo_servicio = IntField(primary_key=True)
    nombre = StringField(required=True, unique=True, max_length=100)
    descripcion = StringField(max_length=255)
    precio = DecimalField(required=True, default=0, precision=2)
    duracion_min = IntField()
    activo = BooleanField(required=True, default=True)


class Reserva(MongoDocument):
    meta = {"collection": "reservas"}
    id_reserva = IntField(primary_key=True)
    id_cliente = IntField(required=True)
    id_vehiculo = IntField(required=True)
    id_tipo_servicio = IntField(required=True)
    id_empleado = IntField()
    fecha_hora = DateTimeField(required=True)
    estado = StringField(required=True, default="Pendiente", max_length=30)

    @property
    def cliente(self):
        return Cliente.objects(pk=self.id_cliente).first()

    @property
    def vehiculo(self):
        return Vehiculo.objects(pk=self.id_vehiculo).first()

    @property
    def tipo(self):
        return TipoServicio.objects(pk=self.id_tipo_servicio).first()

    @property
    def empleado(self):
        return Empleado.objects(pk=self.id_empleado).first() if self.id_empleado else None

    @property
    def servicio(self):
        return Servicio.objects(id_reserva=self.id_reserva).first()


class Servicio(MongoDocument):
    meta = {"collection": "servicios"}
    id_servicio = IntField(primary_key=True)
    id_vehiculo = IntField(required=True)
    id_empleado = IntField(required=True)
    id_reserva = IntField()
    id_tipo_servicio = IntField(required=True)
    fecha_inicio = DateTimeField(required=True, default=datetime.now)
    fecha_fin = DateTimeField()
    tiempo_total = IntField()
    costo = DecimalField(required=True, default=0, precision=2)
    estado = StringField(required=True, default="En espera", max_length=30)

    @property
    def vehiculo(self):
        return Vehiculo.objects(pk=self.id_vehiculo).first()

    @property
    def empleado(self):
        return Empleado.objects(pk=self.id_empleado).first()

    @property
    def tipo(self):
        return TipoServicio.objects(pk=self.id_tipo_servicio).first()

    @property
    def reserva(self):
        return Reserva.objects(pk=self.id_reserva).first() if self.id_reserva else None

    @property
    def comision(self):
        return Comision.objects(id_servicio=self.id_servicio).first()

    @property
    def recibo(self):
        return Recibo.objects(id_servicio=self.id_servicio).first()


class Comision(MongoDocument):
    meta = {"collection": "comisiones"}
    id_comision = IntField(primary_key=True)
    id_servicio = IntField(required=True, unique=True)
    id_empleado = IntField(required=True)
    monto = DecimalField(required=True, default=0, precision=2)
    fecha_calculo = DateTimeField(required=True, default=datetime.now)
    pagada = BooleanField(required=True, default=False)

    @property
    def servicio(self):
        return Servicio.objects(pk=self.id_servicio).first()

    @property
    def empleado(self):
        return Empleado.objects(pk=self.id_empleado).first()


class Recibo(MongoDocument):
    meta = {"collection": "recibos"}
    id_recibo = IntField(primary_key=True)
    id_servicio = IntField(required=True, unique=True)
    fecha_emision = DateTimeField(required=True, default=datetime.now)
    total = DecimalField(required=True, default=0, precision=2)
    email_enviado = BooleanField(required=True, default=False)
    estado = StringField(required=True, default="Pendiente", max_length=30)

    @property
    def servicio(self):
        return Servicio.objects(pk=self.id_servicio).first()


class Negocio(MongoDocument):
    meta = {"collection": "negocio"}
    id = IntField(primary_key=True)
    nombre = StringField(required=True, max_length=150)
    correo = StringField(max_length=150)
    telefono = StringField(max_length=30)
    direccion = StringField(max_length=200)
    meta_mensual = DecimalField(required=True, default=0, precision=2)


class Preferencia(MongoDocument):
    id = IntField(primary_key=True)
    id_usuario = IntField(required=True)
    clave = StringField(required=True, max_length=60)
    valor = BooleanField(required=True, default=False)

    meta = {
        "collection": "preferencias",
        "queryset_class": MongoQuerySet,
        "indexes": [{"fields": ("id_usuario", "clave"), "unique": True}],
    }


for _model in (
    Usuario, Cliente, Vehiculo, Empleado, TipoServicio, Reserva, Servicio,
    Comision, Recibo, Negocio, Preferencia,
):
    db.register(_model)

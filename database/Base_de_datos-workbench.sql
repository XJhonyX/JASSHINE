-- ============================================================
-- SCRIPT: SISTEMA DE LAVADO DE VEHÍCULOS (JASSHINE)
-- BASE DE DATOS: lavado_vehiculos
-- MOTOR: MySQL / MariaDB
--
-- Este script parte del original que compartiste y le aplica los
-- 5 ajustes que revisamos:
--   1) Usuario ahora se conecta con Cliente y Empleado (FK id_usuario)
--   2) Reserva ahora sabe de quién es: cliente, vehículo, tipo de
--      servicio y (opcionalmente) el empleado asignado
--   3) Nueva tabla TipoServicio: catálogo de lavados y precios
--   4) Horario y Disponibilidad se unificaron en una sola tabla
--   5) Empleado ahora tiene teléfono, y los montos de dinero pasan
--      de FLOAT a DECIMAL(10,2) para evitar errores de redondeo
--
-- Cada cambio respecto al original está marcado con "-- AJUSTE:"
-- ============================================================

CREATE DATABASE IF NOT EXISTS lavado_vehiculos
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_spanish_ci;

USE lavado_vehiculos;


-- ============================================================
-- MÓDULO 1: AUTENTICACIÓN
-- ============================================================

CREATE TABLE IF NOT EXISTS Usuario (
    id_usuario  INT             NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)    NOT NULL,
    contrasena  VARCHAR(255)    NOT NULL,
    rol         VARCHAR(50)     NOT NULL,
    PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuario_email UNIQUE (email),
    -- AJUSTE: solo se aceptan estos 3 roles, evita typos como 'Admin' vs 'admin'
    CONSTRAINT chk_usuario_rol CHECK (rol IN ('admin','empleado','cliente'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Sesion (
    id_sesion       INT             NOT NULL AUTO_INCREMENT,
    id_usuario      INT             NOT NULL,
    fecha_inicio    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_fin       DATETIME        NULL,
    token           VARCHAR(512)    NOT NULL,
    PRIMARY KEY (id_sesion),
    CONSTRAINT uq_sesion_token UNIQUE (token),
    INDEX idx_sesion_usuario (id_usuario),
    CONSTRAINT fk_sesion_usuario FOREIGN KEY (id_usuario)
        REFERENCES Usuario(id_usuario)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 2: SELECCIÓN DE CLIENTE
-- ============================================================

CREATE TABLE IF NOT EXISTS Cliente (
    id_cliente  INT             NOT NULL AUTO_INCREMENT,
    -- AJUSTE: conecta el perfil de cliente con su cuenta de acceso
    id_usuario  INT             NOT NULL,
    nombre      VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)    NOT NULL,
    telefono    VARCHAR(20)     NULL,
    PRIMARY KEY (id_cliente),
    CONSTRAINT uq_cliente_email UNIQUE (email),
    CONSTRAINT uq_cliente_usuario UNIQUE (id_usuario),
    CONSTRAINT fk_cliente_usuario FOREIGN KEY (id_usuario)
        REFERENCES Usuario(id_usuario)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Vehiculo (
    id_vehiculo INT             NOT NULL AUTO_INCREMENT,
    id_cliente  INT             NOT NULL,
    tipo        VARCHAR(50)     NOT NULL,
    placa       VARCHAR(20)     NOT NULL,
    PRIMARY KEY (id_vehiculo),
    CONSTRAINT uq_vehiculo_placa UNIQUE (placa),
    INDEX idx_vehiculo_cliente (id_cliente),
    CONSTRAINT fk_vehiculo_cliente FOREIGN KEY (id_cliente)
        REFERENCES Cliente(id_cliente)
        ON DELETE NO ACTION
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 5: GESTIÓN DE EMPLEADOS
-- (se crea antes que Servicio/Reserva por dependencia de FK)
-- ============================================================

CREATE TABLE IF NOT EXISTS Empleado (
    id_empleado     INT             NOT NULL AUTO_INCREMENT,
    -- AJUSTE: conecta el perfil de empleado con su cuenta de acceso
    id_usuario      INT             NOT NULL,
    nombre          VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    -- AJUSTE: el panel de admin ya mostraba teléfono, pero no existía la columna
    telefono        VARCHAR(20)     NULL,
    especialidad    VARCHAR(100)    NULL,
    estado          VARCHAR(30)     NOT NULL DEFAULT 'activo',
    PRIMARY KEY (id_empleado),
    CONSTRAINT uq_empleado_email UNIQUE (email),
    CONSTRAINT uq_empleado_usuario UNIQUE (id_usuario),
    CONSTRAINT fk_empleado_usuario FOREIGN KEY (id_usuario)
        REFERENCES Usuario(id_usuario)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- AJUSTE: Horario y Disponibilidad guardaban lo mismo (empleado + fecha +
-- rango de hora). Se dejan unidas en una sola tabla; "disponible" indica
-- si ese bloque de horario está libre para agendar o ya está ocupado.
CREATE TABLE IF NOT EXISTS Horario (
    id_horario      INT             NOT NULL AUTO_INCREMENT,
    id_empleado     INT             NOT NULL,
    fecha           DATE            NOT NULL,
    hora_inicio     TIME            NOT NULL,
    hora_fin        TIME            NOT NULL,
    disponible      TINYINT(1)      NOT NULL DEFAULT 1,
    PRIMARY KEY (id_horario),
    INDEX idx_horario_empleado (id_empleado),
    CONSTRAINT fk_horario_empleado FOREIGN KEY (id_empleado)
        REFERENCES Empleado(id_empleado)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 4A: CATÁLOGO DE SERVICIOS  (tabla nueva)
-- ============================================================

-- AJUSTE: antes el nombre y el precio del lavado se repetían en cada fila
-- de Servicio como texto libre. Ahora viven en un solo lugar: si cambia el
-- precio de "Lavado básico", se actualiza aquí y ya, sin tocar el historial.
CREATE TABLE IF NOT EXISTS TipoServicio (
    id_tipo_servicio    INT             NOT NULL AUTO_INCREMENT,
    nombre              VARCHAR(100)    NOT NULL,
    descripcion         VARCHAR(255)    NULL,
    precio              DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    duracion_min        INT             NULL,
    activo              TINYINT(1)      NOT NULL DEFAULT 1,
    PRIMARY KEY (id_tipo_servicio),
    CONSTRAINT uq_tiposervicio_nombre UNIQUE (nombre)
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 3: PROGRAMACIONES (RESERVAS)
-- ============================================================

-- AJUSTE: antes Reserva solo tenía fecha_hora y estado, sin saber de quién
-- era la cita. Ahora sí queda registrado el cliente, el vehículo, el tipo
-- de servicio pedido, y (cuando ya se asignó) el empleado.
CREATE TABLE IF NOT EXISTS Reserva (
    id_reserva          INT             NOT NULL AUTO_INCREMENT,
    id_cliente          INT             NOT NULL,
    id_vehiculo         INT             NOT NULL,
    id_tipo_servicio    INT             NOT NULL,
    id_empleado         INT             NULL,
    fecha_hora          DATETIME        NOT NULL,
    estado              VARCHAR(30)     NOT NULL DEFAULT 'pendiente',
    PRIMARY KEY (id_reserva),
    INDEX idx_reserva_cliente (id_cliente),
    INDEX idx_reserva_empleado (id_empleado),
    CONSTRAINT fk_reserva_cliente FOREIGN KEY (id_cliente)
        REFERENCES Cliente(id_cliente)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_reserva_vehiculo FOREIGN KEY (id_vehiculo)
        REFERENCES Vehiculo(id_vehiculo)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_reserva_tiposervicio FOREIGN KEY (id_tipo_servicio)
        REFERENCES TipoServicio(id_tipo_servicio)
        ON DELETE NO ACTION
        ON UPDATE CASCADE,
    CONSTRAINT fk_reserva_empleado FOREIGN KEY (id_empleado)
        REFERENCES Empleado(id_empleado)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 4: EJECUCIÓN DE SERVICIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS Servicio (
    id_servicio         INT             NOT NULL AUTO_INCREMENT,
    id_vehiculo         INT             NOT NULL,
    id_empleado         INT             NOT NULL,
    id_reserva          INT             NULL,
    -- AJUSTE: ahora referencia el catálogo en vez de guardar el nombre como texto
    id_tipo_servicio    INT             NOT NULL,
    fecha_inicio        DATETIME        NOT NULL,
    fecha_fin           DATETIME        NULL,
    tiempo_total         INT             NULL,
    -- AJUSTE: FLOAT -> DECIMAL(10,2). Se mantiene por si el costo real
    -- difiere del precio del catálogo (por ejemplo, con un descuento).
    costo               DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    PRIMARY KEY (id_servicio),
    INDEX idx_servicio_vehiculo (id_vehiculo),
    INDEX idx_servicio_empleado (id_empleado),
    CONSTRAINT fk_servicio_vehiculo FOREIGN KEY (id_vehiculo)
        REFERENCES Vehiculo(id_vehiculo)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT fk_servicio_empleado FOREIGN KEY (id_empleado)
        REFERENCES Empleado(id_empleado)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT fk_servicio_reserva FOREIGN KEY (id_reserva)
        REFERENCES Reserva(id_reserva)
        ON DELETE SET NULL
        ON UPDATE NO ACTION,
    CONSTRAINT fk_servicio_tiposervicio FOREIGN KEY (id_tipo_servicio)
        REFERENCES TipoServicio(id_tipo_servicio)
        ON DELETE NO ACTION
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 6: CÁLCULOS FINANCIEROS
-- ============================================================

-- NOTA (del script original): ON UPDATE NO ACTION en fk_comision_empleado
-- para evitar el ciclo de cascada: Comision -> Empleado <- Servicio -> Empleado

CREATE TABLE IF NOT EXISTS Comision (
    id_comision     INT             NOT NULL AUTO_INCREMENT,
    id_servicio     INT             NOT NULL,
    id_empleado     INT             NOT NULL,
    -- AJUSTE: FLOAT -> DECIMAL(10,2)
    monto           DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    fecha_calculo   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_comision),
    CONSTRAINT uq_comision_servicio UNIQUE (id_servicio),
    INDEX idx_comision_empleado (id_empleado),
    CONSTRAINT fk_comision_servicio FOREIGN KEY (id_servicio)
        REFERENCES Servicio(id_servicio)
        ON DELETE CASCADE
        ON UPDATE NO ACTION,
    CONSTRAINT fk_comision_empleado FOREIGN KEY (id_empleado)
        REFERENCES Empleado(id_empleado)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 7: DOCUMENTACIÓN DE TRANSACCIONES
-- ============================================================

CREATE TABLE IF NOT EXISTS Recibo (
    id_recibo       INT             NOT NULL AUTO_INCREMENT,
    id_servicio     INT             NOT NULL,
    fecha_emision   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- AJUSTE: FLOAT -> DECIMAL(10,2)
    total           DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    email_enviado   TINYINT(1)      NOT NULL DEFAULT 0,
    PRIMARY KEY (id_recibo),
    CONSTRAINT uq_recibo_servicio UNIQUE (id_servicio),
    CONSTRAINT fk_recibo_servicio FOREIGN KEY (id_servicio)
        REFERENCES Servicio(id_servicio)
        ON DELETE CASCADE
        ON UPDATE NO ACTION
) ENGINE=InnoDB;


-- ============================================================
-- DATOS DE EJEMPLO
-- Cada INSERT verifica que el registro no exista antes de insertar
-- ============================================================

-- Usuarios (uno por rol, como en tu login con selector Admin/Empleado/Cliente)
INSERT INTO Usuario (nombre, email, contrasena, rol)
SELECT 'Administrador', 'admin@lavado.com', '$2b$12$ejemplo_hash_aqui', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM Usuario WHERE email = 'admin@lavado.com');

INSERT INTO Usuario (nombre, email, contrasena, rol)
SELECT 'Carlos López', 'carlos@lavado.com', '$2b$12$ejemplo_hash_aqui', 'empleado'
WHERE NOT EXISTS (SELECT 1 FROM Usuario WHERE email = 'carlos@lavado.com');

INSERT INTO Usuario (nombre, email, contrasena, rol)
SELECT 'Juan Pérez', 'juan@email.com', '$2b$12$ejemplo_hash_aqui', 'cliente'
WHERE NOT EXISTS (SELECT 1 FROM Usuario WHERE email = 'juan@email.com');

-- Catálogo de servicios (igual a lo que ya se ve en la página)
INSERT INTO TipoServicio (nombre, descripcion, precio, duracion_min)
SELECT 'Lavado básico', 'Exterior completo', 8000.00, 20
WHERE NOT EXISTS (SELECT 1 FROM TipoServicio WHERE nombre = 'Lavado básico');

INSERT INTO TipoServicio (nombre, descripcion, precio, duracion_min)
SELECT 'Lavado completo', 'Exterior + interior', 15000.00, 35
WHERE NOT EXISTS (SELECT 1 FROM TipoServicio WHERE nombre = 'Lavado completo');

INSERT INTO TipoServicio (nombre, descripcion, precio, duracion_min)
SELECT 'Lavado + Pulido', 'Brillo de todas las piezas', 22000.00, 55
WHERE NOT EXISTS (SELECT 1 FROM TipoServicio WHERE nombre = 'Lavado + Pulido');

INSERT INTO TipoServicio (nombre, descripcion, precio, duracion_min)
SELECT 'Lavado Full', 'Interior, exterior y pulida', 25000.00, 70
WHERE NOT EXISTS (SELECT 1 FROM TipoServicio WHERE nombre = 'Lavado Full');

-- Cliente (conectado a su Usuario)
INSERT INTO Cliente (id_usuario, nombre, email, telefono)
SELECT u.id_usuario, 'Juan Pérez', 'juan@email.com', '3001234567'
FROM Usuario u WHERE u.email = 'juan@email.com'
AND NOT EXISTS (SELECT 1 FROM Cliente WHERE email = 'juan@email.com');

INSERT INTO Vehiculo (id_cliente, tipo, placa)
SELECT c.id_cliente, 'SUV', 'ABC-123'
FROM Cliente c WHERE c.email = 'juan@email.com'
AND NOT EXISTS (SELECT 1 FROM Vehiculo WHERE placa = 'ABC-123');

-- Empleado (conectado a su Usuario)
INSERT INTO Empleado (id_usuario, nombre, email, telefono, especialidad, estado)
SELECT u.id_usuario, 'Carlos López', 'carlos@lavado.com', '3009876543', 'Lavado completo', 'activo'
FROM Usuario u WHERE u.email = 'carlos@lavado.com'
AND NOT EXISTS (SELECT 1 FROM Empleado WHERE email = 'carlos@lavado.com');

-- ============================================================
-- FIN DEL SCRIPT
-- ============================================================

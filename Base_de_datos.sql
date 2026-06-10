-- ============================================================
-- SCRIPT: SISTEMA DE LAVADO DE VEHÍCULOS
-- BASE DE DATOS: lavado_vehiculos
-- MOTOR: SQL Server (SSMS)
-- ============================================================

IF NOT EXISTS (
    SELECT name FROM sys.databases WHERE name = 'lavado_vehiculos'
)
BEGIN
    CREATE DATABASE lavado_vehiculos
    COLLATE Modern_Spanish_CI_AI;
END
GO

USE lavado_vehiculos;
GO


-- ============================================================
-- MÓDULO 1: AUTENTICACIÓN
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Usuario') AND type = 'U')
BEGIN
    CREATE TABLE Usuario (
        id_usuario  INT             NOT NULL IDENTITY(1,1),
        nombre      VARCHAR(100)    NOT NULL,
        email       VARCHAR(150)    NOT NULL,
        contrasena  VARCHAR(255)    NOT NULL,
        rol         VARCHAR(50)     NOT NULL,
        CONSTRAINT pk_usuario       PRIMARY KEY (id_usuario),
        CONSTRAINT uq_usuario_email UNIQUE      (email)
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Sesion') AND type = 'U')
BEGIN
    CREATE TABLE Sesion (
        id_sesion       INT             NOT NULL IDENTITY(1,1),
        id_usuario      INT             NOT NULL,
        fecha_inicio    DATETIME        NOT NULL DEFAULT GETDATE(),
        fecha_fin       DATETIME,
        token           VARCHAR(512)    NOT NULL,
        CONSTRAINT pk_sesion            PRIMARY KEY (id_sesion),
        CONSTRAINT uq_sesion_token      UNIQUE      (token),
        CONSTRAINT fk_sesion_usuario    FOREIGN KEY (id_usuario)
            REFERENCES Usuario(id_usuario)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_sesion_usuario' AND object_id = OBJECT_ID('dbo.Sesion'))
    CREATE INDEX idx_sesion_usuario ON Sesion(id_usuario);
GO


-- ============================================================
-- MÓDULO 2: SELECCIÓN DE CLIENTE
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Cliente') AND type = 'U')
BEGIN
    CREATE TABLE Cliente (
        id_cliente  INT             NOT NULL IDENTITY(1,1),
        nombre      VARCHAR(100)    NOT NULL,
        email       VARCHAR(150)    NOT NULL,
        telefono    VARCHAR(20),
        CONSTRAINT pk_cliente       PRIMARY KEY (id_cliente),
        CONSTRAINT uq_cliente_email UNIQUE      (email)
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Vehiculo') AND type = 'U')
BEGIN
    CREATE TABLE Vehiculo (
        id_vehiculo INT             NOT NULL IDENTITY(1,1),
        id_cliente  INT             NOT NULL,
        tipo        VARCHAR(50)     NOT NULL,
        placa       VARCHAR(20)     NOT NULL,
        CONSTRAINT pk_vehiculo          PRIMARY KEY (id_vehiculo),
        CONSTRAINT uq_vehiculo_placa    UNIQUE      (placa),
        CONSTRAINT fk_vehiculo_cliente  FOREIGN KEY (id_cliente)
            REFERENCES Cliente(id_cliente)
            ON DELETE NO ACTION
            ON UPDATE CASCADE
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_vehiculo_cliente' AND object_id = OBJECT_ID('dbo.Vehiculo'))
    CREATE INDEX idx_vehiculo_cliente ON Vehiculo(id_cliente);
GO


-- ============================================================
-- MÓDULO 3: PROGRAMACIONES (RESERVAS)
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Reserva') AND type = 'U')
BEGIN
    CREATE TABLE Reserva (
        id_reserva  INT             NOT NULL IDENTITY(1,1),
        fecha_hora  DATETIME        NOT NULL,
        estado      VARCHAR(30)     NOT NULL DEFAULT 'pendiente',
        CONSTRAINT pk_reserva PRIMARY KEY (id_reserva)
    );
END
GO


-- ============================================================
-- MÓDULO 5: GESTIÓN DE EMPLEADOS
-- (Se crea antes de Servicio por dependencia de FK)
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Empleado') AND type = 'U')
BEGIN
    CREATE TABLE Empleado (
        id_empleado     INT             NOT NULL IDENTITY(1,1),
        nombre          VARCHAR(100)    NOT NULL,
        email           VARCHAR(150)    NOT NULL,
        especialidad    VARCHAR(100),
        estado          VARCHAR(30)     NOT NULL DEFAULT 'activo',
        CONSTRAINT pk_empleado          PRIMARY KEY (id_empleado),
        CONSTRAINT uq_empleado_email    UNIQUE      (email)
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Horario') AND type = 'U')
BEGIN
    CREATE TABLE Horario (
        id_horario      INT             NOT NULL IDENTITY(1,1),
        id_empleado     INT             NOT NULL,
        fecha           DATE            NOT NULL,
        hora_inicio     TIME            NOT NULL,
        hora_fin        TIME            NOT NULL,
        disponible      BIT             NOT NULL DEFAULT 1,
        CONSTRAINT pk_horario           PRIMARY KEY (id_horario),
        CONSTRAINT fk_horario_empleado  FOREIGN KEY (id_empleado)
            REFERENCES Empleado(id_empleado)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_horario_empleado' AND object_id = OBJECT_ID('dbo.Horario'))
    CREATE INDEX idx_horario_empleado ON Horario(id_empleado);
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Disponibilidad') AND type = 'U')
BEGIN
    CREATE TABLE Disponibilidad (
        id_disponibilidad   INT     NOT NULL IDENTITY(1,1),
        id_empleado         INT     NOT NULL,
        fecha               DATE    NOT NULL,
        hora_inicio         TIME    NOT NULL,
        hora_fin            TIME    NOT NULL,
        CONSTRAINT pk_disponibilidad            PRIMARY KEY (id_disponibilidad),
        CONSTRAINT fk_disponibilidad_empleado   FOREIGN KEY (id_empleado)
            REFERENCES Empleado(id_empleado)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    );
END
GO


-- ============================================================
-- MÓDULO 4: EJECUCIÓN DE SERVICIOS
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Servicio') AND type = 'U')
BEGIN
    CREATE TABLE Servicio (
        id_servicio     INT             NOT NULL IDENTITY(1,1),
        id_vehiculo     INT             NOT NULL,
        id_empleado     INT             NOT NULL,
        id_reserva      INT,
        tipo_lavado     VARCHAR(100)    NOT NULL,
        fecha_inicio    DATETIME        NOT NULL,
        fecha_fin       DATETIME,
        tiempo_total    INT,
        costo           FLOAT           NOT NULL DEFAULT 0.0,
        CONSTRAINT pk_servicio          PRIMARY KEY (id_servicio),
        CONSTRAINT fk_servicio_vehiculo FOREIGN KEY (id_vehiculo)
            REFERENCES Vehiculo(id_vehiculo)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT fk_servicio_empleado FOREIGN KEY (id_empleado)
            REFERENCES Empleado(id_empleado)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION,
        CONSTRAINT fk_servicio_reserva  FOREIGN KEY (id_reserva)
            REFERENCES Reserva(id_reserva)
            ON DELETE SET NULL
            ON UPDATE NO ACTION
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_servicio_vehiculo' AND object_id = OBJECT_ID('dbo.Servicio'))
    CREATE INDEX idx_servicio_vehiculo ON Servicio(id_vehiculo);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_servicio_empleado' AND object_id = OBJECT_ID('dbo.Servicio'))
    CREATE INDEX idx_servicio_empleado ON Servicio(id_empleado);
GO


-- ============================================================
-- MÓDULO 6: CÁLCULOS FINANCIEROS
-- ============================================================

-- NOTA: ON UPDATE NO ACTION en fk_comision_empleado para evitar
-- el ciclo de cascada: Comision → Empleado ← Servicio → Empleado

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Comision') AND type = 'U')
BEGIN
    CREATE TABLE Comision (
        id_comision     INT             NOT NULL IDENTITY(1,1),
        id_servicio     INT             NOT NULL,
        id_empleado     INT             NOT NULL,
        monto           FLOAT           NOT NULL DEFAULT 0.0,
        fecha_calculo   DATETIME        NOT NULL DEFAULT GETDATE(),
        CONSTRAINT pk_comision              PRIMARY KEY (id_comision),
        CONSTRAINT uq_comision_servicio     UNIQUE      (id_servicio),
        CONSTRAINT fk_comision_servicio     FOREIGN KEY (id_servicio)
            REFERENCES Servicio(id_servicio)
            ON DELETE CASCADE
            ON UPDATE NO ACTION,
        CONSTRAINT fk_comision_empleado     FOREIGN KEY (id_empleado)
            REFERENCES Empleado(id_empleado)
            ON DELETE NO ACTION
            ON UPDATE NO ACTION
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_comision_empleado' AND object_id = OBJECT_ID('dbo.Comision'))
    CREATE INDEX idx_comision_empleado ON Comision(id_empleado);
GO


-- ============================================================
-- MÓDULO 7: DOCUMENTACIÓN DE TRANSACCIONES
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Recibo') AND type = 'U')
BEGIN
    CREATE TABLE Recibo (
        id_recibo       INT             NOT NULL IDENTITY(1,1),
        id_servicio     INT             NOT NULL,
        fecha_emision   DATETIME        NOT NULL DEFAULT GETDATE(),
        total           FLOAT           NOT NULL DEFAULT 0.0,
        email_enviado   BIT             NOT NULL DEFAULT 0,
        CONSTRAINT pk_recibo            PRIMARY KEY (id_recibo),
        CONSTRAINT uq_recibo_servicio   UNIQUE      (id_servicio),
        CONSTRAINT fk_recibo_servicio   FOREIGN KEY (id_servicio)
            REFERENCES Servicio(id_servicio)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
    );
END
GO


-- ============================================================
-- DATOS DE EJEMPLO
-- Cada INSERT verifica que el registro no exista antes de insertar
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM Usuario WHERE email = 'admin@lavado.com')
    INSERT INTO Usuario (nombre, email, contrasena, rol)
    VALUES ('Administrador', 'admin@lavado.com', '$2b$12$ejemplo_hash_aqui', 'admin');
GO

IF NOT EXISTS (SELECT 1 FROM Cliente WHERE email = 'juan@email.com')
    INSERT INTO Cliente (nombre, email, telefono)
    VALUES ('Juan Pérez', 'juan@email.com', '3001234567');
GO

IF NOT EXISTS (SELECT 1 FROM Vehiculo WHERE placa = 'ABC-123')
    INSERT INTO Vehiculo (id_cliente, tipo, placa)
    VALUES (1, 'SUV', 'ABC-123');
GO

IF NOT EXISTS (SELECT 1 FROM Empleado WHERE email = 'carlos@lavado.com')
    INSERT INTO Empleado (nombre, email, especialidad, estado)
    VALUES ('Carlos López', 'carlos@lavado.com', 'Lavado completo', 'activo');
GO

-- ============================================================
-- FIN DEL SCRIPT
-- ============================================================
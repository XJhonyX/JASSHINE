-- ============================================================
-- SCRIPT: SISTEMA DE LAVADO DE VEHÍCULOS
-- BASE DE DATOS: lavado_vehiculos
-- MOTOR: MySQL (SQL Workbench / MySQL Workbench)
-- Convertido desde script original de SQL Server (SSMS)
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
    CONSTRAINT uq_usuario_email UNIQUE (email)
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
    nombre      VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)    NOT NULL,
    telefono    VARCHAR(20)     NULL,
    PRIMARY KEY (id_cliente),
    CONSTRAINT uq_cliente_email UNIQUE (email)
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
-- MÓDULO 3: PROGRAMACIONES (RESERVAS)
-- ============================================================

CREATE TABLE IF NOT EXISTS Reserva (
    id_reserva  INT             NOT NULL AUTO_INCREMENT,
    fecha_hora  DATETIME        NOT NULL,
    estado      VARCHAR(30)     NOT NULL DEFAULT 'pendiente',
    PRIMARY KEY (id_reserva)
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 5: GESTIÓN DE EMPLEADOS
-- (Se crea antes de Servicio por dependencia de FK)
-- ============================================================

CREATE TABLE IF NOT EXISTS Empleado (
    id_empleado     INT             NOT NULL AUTO_INCREMENT,
    nombre          VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    especialidad    VARCHAR(100)    NULL,
    estado          VARCHAR(30)     NOT NULL DEFAULT 'activo',
    PRIMARY KEY (id_empleado),
    CONSTRAINT uq_empleado_email UNIQUE (email)
) ENGINE=InnoDB;

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

CREATE TABLE IF NOT EXISTS Disponibilidad (
    id_disponibilidad  INT     NOT NULL AUTO_INCREMENT,
    id_empleado        INT     NOT NULL,
    fecha               DATE    NOT NULL,
    hora_inicio         TIME    NOT NULL,
    hora_fin             TIME    NOT NULL,
    PRIMARY KEY (id_disponibilidad),
    CONSTRAINT fk_disponibilidad_empleado FOREIGN KEY (id_empleado)
        REFERENCES Empleado(id_empleado)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 4: EJECUCIÓN DE SERVICIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS Servicio (
    id_servicio     INT             NOT NULL AUTO_INCREMENT,
    id_vehiculo     INT             NOT NULL,
    id_empleado     INT             NOT NULL,
    id_reserva      INT             NULL,
    tipo_lavado     VARCHAR(100)    NOT NULL,
    fecha_inicio    DATETIME        NOT NULL,
    fecha_fin       DATETIME        NULL,
    tiempo_total    INT             NULL,
    costo           FLOAT           NOT NULL DEFAULT 0.0,
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
        ON UPDATE NO ACTION
) ENGINE=InnoDB;


-- ============================================================
-- MÓDULO 6: CÁLCULOS FINANCIEROS
-- ============================================================

-- NOTA: ON UPDATE NO ACTION en fk_comision_empleado para evitar
-- el ciclo de cascada: Comision -> Empleado <- Servicio -> Empleado

CREATE TABLE IF NOT EXISTS Comision (
    id_comision     INT             NOT NULL AUTO_INCREMENT,
    id_servicio     INT             NOT NULL,
    id_empleado     INT             NOT NULL,
    monto           FLOAT           NOT NULL DEFAULT 0.0,
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
    total           FLOAT           NOT NULL DEFAULT 0.0,
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

INSERT INTO Usuario (nombre, email, contrasena, rol)
SELECT 'Administrador', 'admin@lavado.com', '$2b$12$ejemplo_hash_aqui', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM Usuario WHERE email = 'admin@lavado.com');

INSERT INTO Cliente (nombre, email, telefono)
SELECT 'Juan Pérez', 'juan@email.com', '3001234567'
WHERE NOT EXISTS (SELECT 1 FROM Cliente WHERE email = 'juan@email.com');

INSERT INTO Vehiculo (id_cliente, tipo, placa)
SELECT 1, 'SUV', 'ABC-123'
WHERE NOT EXISTS (SELECT 1 FROM Vehiculo WHERE placa = 'ABC-123');

INSERT INTO Empleado (nombre, email, especialidad, estado)
SELECT 'Carlos López', 'carlos@lavado.com', 'Lavado completo', 'activo'
WHERE NOT EXISTS (SELECT 1 FROM Empleado WHERE email = 'carlos@lavado.com');

-- ============================================================
-- FIN DEL SCRIPT
-- ============================================================

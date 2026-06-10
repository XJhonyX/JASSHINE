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

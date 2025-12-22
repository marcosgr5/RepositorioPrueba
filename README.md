# Sistema Distribuido con ZeroC IceGrid

![ZeroC Ice](https://img.shields.io/badge/Middleware-ZeroC_Ice-blue)
![Language](https://img.shields.io/badge/Language-Python-orange)
![Deploy](https://img.shields.io/badge/Deploy-IceGrid-green)

Este repositorio contiene la implementación de una aplicación distribuida utilizando el middleware **ZeroC Ice**. El proyecto se centra en el uso del servicio **IceGrid** para gestionar el despliegue, la localización de objetos y la activación de servidores bajo demanda.

## 📋 Descripción del Proyecto

El objetivo de este sistema es demostrar las capacidades de una arquitectura distribuida robusta. A diferencia de una conexión directa simple (cliente-servidor), este proyecto utiliza un **Registro (IceGrid Registry)** y **Nodos** para gestionar la infraestructura.

### Características Principales
* **Transparencia de Ubicación:** Los clientes no necesitan saber la IP/Puerto del servidor, solo el nombre del objeto.
* **Activación bajo demanda:** Los servidores se inician automáticamente cuando un cliente realiza una petición.
* **Gestión Centralizada:** Uso de descriptores XML para definir la topología de la red.

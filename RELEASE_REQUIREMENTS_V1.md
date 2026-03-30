# Requisitos de Publicacion v1.0.0

## Objetivo
Definir una salida v1.0.0 estable, instalable y verificable end-to-end con bootstrap inteligente del entorno.

## Gate obligatorio para v1.0.0

- [ ] E2E verde para GUI, servidor web y all-in-one.
- [ ] Auditoria de recursos obligatorios sin faltantes.
- [ ] Seguridad base validada (auth, rutas protegidas, path traversal, sanitizacion).
- [ ] Sin dependencias HIGH/CRITICAL vulnerables en auditoria de paquetes.
- [ ] Instalacion inicial reproducible en Windows limpio.

## Bootstrap inteligente (parche previo recomendado)

### Flujo de arranque esperado

1. Detectar prerequisitos locales (Python runtime embebido si aplica, Ollama, permisos de escritura, puertos).
2. Verificar estructura minima de recursos (templates, static, assets, carpeta de trabajo).
3. Si falta un recurso recuperable, descargarlo o reinstalarlo automaticamente desde una fuente confiable.
4. Si falta dependencia no recuperable de forma automatica, guiar al usuario con accion puntual y boton de reintento.
5. Ejecutar autodiagnostico final y dejar el sistema en estado READY antes de abrir UI principal.

### Requisitos tecnicos del bootstrap

- Manifest versionado de recursos requeridos (nombre, hash, tamano, origen, version minima).
- Verificacion de integridad por hash antes de usar cualquier recurso descargado.
- Cache local de paquetes/artefactos para reinstalacion rapida sin descarga redundante.
- Reintentos con backoff y timeout por paso (sin bloquear indefinidamente).
- Modo offline degradado: permitir uso parcial cuando el recurso faltante no es critico.
- Registro de eventos de bootstrap en logs auditables.

### UX minima del bootstrap

- Barra de progreso con etapa actual (detectar, validar, descargar, aplicar, verificar).
- Mensaje claro de estado final: READY, READY_WITH_WARNINGS o BLOCKED.
- Acciones de recuperacion visibles: Reintentar, Abrir carpeta, Ver log.

## Checklist de evidencias para liberar v1.0.0

- Reporte E2E actualizado (`RELEASE_AUDIT.md`).
- Matriz de compatibilidad minima por sistema operativo.
- Lista de recursos versionados y su hash.
- Instrucciones de rollback para version anterior.
- Changelog con cambios breaking/non-breaking.

## Criterio de bloqueo

Si el bootstrap no deja el entorno en estado READY o READY_WITH_WARNINGS, no se autoriza publicacion v1.0.0.

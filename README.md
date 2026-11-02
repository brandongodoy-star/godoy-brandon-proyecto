# godoy-brandon-proyecto

API de un taller mecánico hecha con FastAPI y SQLite.

## Cómo ejecutarla (PowerShell)

1. Crea el entorno virtual e instala las dependencias:

   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Define la clave secreta que firma los tokens. La app no arranca sin ella y no debe subirse a Git:

   ```powershell
   $env:TALLER_CLAVE_SECRETA = python -c "import secrets; print(secrets.token_hex(32))"
   ```

   La variable dura lo que dure esa terminal. Si cambias la clave, los tokens anteriores dejan de servir.

3. Inicia la API. La primera vez crea `taller.db` a partir de `crear_bd.sql`:

   ```powershell
   uvicorn main:app --reload
   ```

   La documentación queda en http://127.0.0.1:8000/docs

## Pruebas

```powershell
pytest
```

Las pruebas usan una base temporal y su propia clave, así que no tocan `taller.db`.

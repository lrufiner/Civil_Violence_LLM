# Instrucciones para subir el repositorio a GitHub

## Pasos para crear y subir el repositorio

### 1. Crear el repositorio en GitHub

1. Ve a [GitHub](https://github.com) e inicia sesión
2. Haz clic en el botón **"+"** en la esquina superior derecha
3. Selecciona **"New repository"**
4. Configura el repositorio:
   - **Repository name**: `Civil_Violence_LLM`
   - **Description**: "Civil Violence model with LLM-based agent decision making"
   - **Visibility**: Público o Privado (según tu preferencia)
   - ⚠️ **NO** marques "Initialize this repository with a README" (ya tenemos uno)
   - ⚠️ **NO** agregues .gitignore ni license (ya los tenemos)
5. Haz clic en **"Create repository"**

### 2. Conectar tu repositorio local con GitHub

Una vez creado el repositorio en GitHub, copia la URL del repositorio (debe verse como: `https://github.com/TU_USUARIO/Civil_Violence_LLM.git`)

Luego ejecuta estos comandos en tu terminal:

```bash
cd /home/lrufiner/Descargas/ReposCodigo/Civil_Violence_LLM

# Agregar el remote de GitHub (reemplaza TU_USUARIO con tu usuario de GitHub)
git remote add origin https://github.com/TU_USUARIO/Civil_Violence_LLM.git

# Verificar que se agregó correctamente
git remote -v

# Subir el código a GitHub
git push -u origin main
```

### 3. Autenticación (si es necesario)

Si GitHub te pide autenticación, puedes usar:

**Opción A: GitHub CLI (recomendado)**
```bash
gh auth login
```

**Opción B: Token de acceso personal (PAT)**
1. Ve a GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Genera un nuevo token con permisos de "repo"
3. Copia el token
4. Cuando hagas `git push`, usa el token como contraseña

**Opción C: SSH (más seguro)**
```bash
# Generar clave SSH
ssh-keygen -t ed25519 -C "lrufiner@sinc.unl.edu.ar"

# Agregar la clave al ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copiar la clave pública
cat ~/.ssh/id_ed25519.pub
# Copia el output y agrégalo en GitHub Settings → SSH and GPG keys

# Cambiar el remote a SSH
git remote set-url origin git@github.com:TU_USUARIO/Civil_Violence_LLM.git
```

### 4. Comandos útiles para después

```bash
# Ver el estado del repositorio
git status

# Ver el historial de commits
git log --oneline

# Agregar cambios y hacer commit
git add .
git commit -m "Descripción de los cambios"

# Subir cambios a GitHub
git push

# Traer cambios de GitHub
git pull
```

### 5. Actualizar el README con tu usuario

No olvides actualizar el README.md con tu usuario real de GitHub en la sección de instalación:

```bash
git clone https://github.com/TU_USUARIO/Civil_Violence_LLM.git
```

Reemplaza `TU_USUARIO` con tu usuario actual de GitHub.

---

## Estado actual del repositorio

✅ Repositorio local inicializado
✅ Commit inicial creado
✅ Archivos incluidos:
  - `.gitignore` (ignora .venv, __pycache__, logs, etc.)
  - `README.md` (documentación completa)
  - `LICENSE` (MIT License)
  - `agents.py` (agentes del modelo)
  - `model.py` (modelo de simulación)
  - `app.py` (interfaz de visualización)
  - `requirements.txt` (dependencias)

🔄 Pendiente: Conectar con GitHub y hacer push

---

## Problemas comunes

### Error: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/TU_USUARIO/Civil_Violence_LLM.git
```

### Error: "failed to push some refs"
```bash
git pull origin main --rebase
git push -u origin main
```

### Error de autenticación
- Usa GitHub CLI: `gh auth login`
- O usa un token de acceso personal en lugar de tu contraseña

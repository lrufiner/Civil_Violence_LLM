#!/bin/bash

# Script para subir el repositorio a GitHub
# Uso: ./push_to_github.sh TU_USUARIO

if [ -z "$1" ]; then
    echo "❌ Error: Debes proporcionar tu usuario de GitHub"
    echo "Uso: ./push_to_github.sh TU_USUARIO"
    echo "Ejemplo: ./push_to_github.sh lrufiner"
    exit 1
fi

GITHUB_USER=$1
REPO_NAME="Civil_Violence_LLM"
REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo "🚀 Configurando repositorio para GitHub..."
echo "Usuario: $GITHUB_USER"
echo "Repositorio: $REPO_NAME"
echo "URL: $REPO_URL"
echo ""

# Verificar si ya existe el remote
if git remote | grep -q "origin"; then
    echo "⚠️  Remote 'origin' ya existe. Actualizando URL..."
    git remote set-url origin $REPO_URL
else
    echo "➕ Agregando remote 'origin'..."
    git remote add origin $REPO_URL
fi

# Mostrar remotes
echo ""
echo "📋 Remotes configurados:"
git remote -v

echo ""
echo "✅ Configuración completada!"
echo ""
echo "📤 Ahora puedes subir tu código con:"
echo "   git push -u origin main"
echo ""
echo "💡 Si es tu primera vez, GitHub te pedirá autenticación."
echo "   Puedes usar:"
echo "   - GitHub CLI: gh auth login"
echo "   - Token de acceso personal (PAT)"
echo "   - SSH (recomendado para uso frecuente)"
echo ""
echo "📖 Para más información, lee GITHUB_SETUP.md"

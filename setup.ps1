# Setup Script for Qdrant-Based RAG Backend
# Run this script to install all dependencies

Write-Host "🚀 Setting up Learnix RAG Backend with Qdrant..." -ForegroundColor Green
Write-Host ""

# Check if Python is available
Write-Host "Checking Python installation..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Python found" -ForegroundColor Green
Write-Host ""

# Change to backend directory
Set-Location backend

# Check if virtual environment exists
if (Test-Path "venv") {
    Write-Host "📦 Virtual environment already exists" -ForegroundColor Cyan
} else {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
Write-Host "✅ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Upgrade pip
Write-Host "⬆️  Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host ""

# Install requirements
Write-Host "📥 Installing dependencies from requirements.txt..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first install (downloading models)..." -ForegroundColor Cyan
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✅ All dependencies installed successfully" -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Creating template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    Write-Host "⚠️  Please update .env with your Qdrant and Gemini API keys" -ForegroundColor Red
} else {
    Write-Host "✅ .env file found" -ForegroundColor Green
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✨ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update .env file with your API keys:" -ForegroundColor White
Write-Host "   - QDRANT_URL" -ForegroundColor Cyan
Write-Host "   - QDRANT_API_KEY" -ForegroundColor Cyan
Write-Host "   - GEMINI_API_KEY" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Run the server:" -ForegroundColor White
Write-Host "   uvicorn app:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Test the health endpoint:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 For more details, see QDRANT_MIGRATION.md" -ForegroundColor Yellow

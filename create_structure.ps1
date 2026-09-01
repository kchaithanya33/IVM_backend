# ============================================================
# Notification Frontend - Project Structure
# Azure Automation Workflow
# ============================================================

$projectName = "notification-frontend"

# ============================================================
# CREATE PROJECT FOLDER
# ============================================================

New-Item -ItemType Directory -Force -Path $projectName | Out-Null

# Move into project folder
Set-Location $projectName

# ============================================================
# FOLDERS
# ============================================================

$folders = @(

    # -------------------------
    # Public
    # -------------------------
    "public",
    "public\icons",

    # -------------------------
    # Source
    # -------------------------
    "src",
    "src\assets",
    "src\assets\images",

    # -------------------------
    # Components
    # -------------------------
    "src\components",

    # Common components
    "src\components\common",

    # Layout
    "src\components\layout",

    # Wizard
    "src\components\wizard",

    # -------------------------
    # Pages
    # -------------------------
    "src\pages",

    # -------------------------
    # Services
    # -------------------------
    "src\services",

    # -------------------------
    # Hooks
    # -------------------------
    "src\hooks",

    # -------------------------
    # Context
    # -------------------------
    "src\context",

    # -------------------------
    # Utils
    # -------------------------
    "src\utils",

    # -------------------------
    # Routes
    # -------------------------
    "src\routes"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
}

# ============================================================
# FILES
# ============================================================

$files = @(

    # ========================================================
    # PUBLIC
    # ========================================================

    "public\logo.svg",

    # ========================================================
    # COMMON COMPONENTS
    # ========================================================

    "src\components\common\Button.jsx",
    "src\components\common\Input.jsx",
    "src\components\common\Select.jsx",
    "src\components\common\RadioCard.jsx",
    "src\components\common\Modal.jsx",
    "src\components\common\Loader.jsx",
    "src\components\common\Toast.jsx",
    "src\components\common\ErrorMessage.jsx",

    # ========================================================
    # LAYOUT
    # ========================================================

    "src\components\layout\Header.jsx",
    "src\components\layout\Sidebar.jsx",
    "src\components\layout\PageLayout.jsx",

    # ========================================================
    # WIZARD
    # ========================================================

    "src\components\wizard\WizardSidebar.jsx",
    "src\components\wizard\WizardHeader.jsx",
    "src\components\wizard\StepIndicator.jsx",
    "src\components\wizard\InfrastructureForm.jsx",
    "src\components\wizard\ConfigurationForm.jsx",
    "src\components\wizard\WizardFooter.jsx",

    # ========================================================
    # PAGES
    # ========================================================

    "src\pages\Dashboard.jsx",
    "src\pages\NewDeployment.jsx",
    "src\pages\DeploymentResult.jsx",

    # ========================================================
    # SERVICES
    # ========================================================

    "src\services\api.js",
    "src\services\deploymentService.js",
    "src\services\subscriptionService.js",
    "src\services\resourceService.js",

    # ========================================================
    # HOOKS
    # ========================================================

    "src\hooks\useDeployment.js",
    "src\hooks\useSubscriptions.js",

    # ========================================================
    # CONTEXT
    # ========================================================

    "src\context\DeploymentContext.jsx",

    # ========================================================
    # UTILS
    # ========================================================

    "src\utils\validators.js",
    "src\utils\constants.js",
    "src\utils\formatters.js",

    # ========================================================
    # ROUTES
    # ========================================================

    "src\routes\AppRoutes.jsx",

    # ========================================================
    # MAIN REACT FILES
    # ========================================================

    "src\App.jsx",
    "src\main.jsx",
    "src\index.css",

    # ========================================================
    # ROOT CONFIGURATION
    # ========================================================

    "package.json",
    "vite.config.js",
    "index.html",

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    ".env",
    ".env.example",

    # ========================================================
    # GIT
    # ========================================================

    ".gitignore",

    # ========================================================
    # DOCUMENTATION
    # ========================================================

    "README.md"
)

foreach ($file in $files) {
    New-Item -ItemType File -Force -Path $file | Out-Null
}

# ============================================================
# SUCCESS MESSAGE
# ============================================================

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " Notification Frontend Structure Created!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""

Write-Host "Project location:" -ForegroundColor Cyan
Write-Host (Get-Location)

Write-Host ""
Write-Host "Structure:" -ForegroundColor Cyan

tree /F

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " Done!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
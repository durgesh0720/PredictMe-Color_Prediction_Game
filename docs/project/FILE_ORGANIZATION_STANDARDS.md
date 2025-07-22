# File Organization Standards for WebSocket_Test Project

## 📁 **Directory Structure Overview**

This document establishes strict file organization standards to maintain a clean, scalable, and maintainable project structure.

## 🎯 **Core Principles**

1. **Root Directory Minimalism**: Keep only essential project files in the root
2. **Logical Categorization**: Group related files in appropriate subdirectories
3. **Consistent Naming**: Use clear, descriptive names following established conventions
4. **No Duplicates**: Maintain single source of truth for all files
5. **Documentation First**: Document all organizational decisions

## 📂 **Approved Directory Structure**

```
WebSocket_Test/
├── 📁 Core Application (Essential Only)
│   ├── manage.py              # Django management command
│   ├── requirements.txt       # Production dependencies
│   ├── requirements-test.txt  # Test dependencies
│   ├── pytest.ini            # Test configuration
│   ├── db.sqlite3            # Development database
│   └── README.md             # Main project documentation
│
├── 📁 polling/               # Main Django application
├── 📁 server/               # Django project settings
├── 📁 templates/            # HTML templates
├── 📁 static/              # CSS, JS, images
├── 📁 media/               # User uploaded files
│
├── 📁 docs/                # ALL documentation goes here
│   ├── admin/              # Admin panel documentation
│   ├── api/               # API documentation
│   ├── email/             # Email setup guides
│   ├── project/           # Project management docs
│   │   ├── reports/       # Analysis and review reports
│   │   ├── fixes/         # Fix documentation
│   │   └── guidelines/    # Project guidelines
│   ├── solutions/         # Problem solutions
│   │   ├── admin/         # Admin-related solutions
│   │   ├── betting/       # Betting system solutions
│   │   └── websocket/     # WebSocket solutions
│   ├── system/            # Technical documentation
│   └── user/              # User guides
│
├── 📁 scripts/             # ALL utility scripts go here
│   ├── admin/             # Admin management scripts
│   ├── data/              # Data operations
│   ├── deployment/        # Deployment scripts
│   ├── development/       # Development tools
│   ├── maintenance/       # System maintenance
│   ├── monitoring/        # Health checks and monitoring
│   ├── setup/             # Initial setup scripts
│   └── utilities/         # General utility scripts
│
├── 📁 tests/               # ALL test files go here
│   ├── admin/             # Admin panel tests
│   ├── integration/       # Integration tests
│   ├── payment/           # Payment system tests
│   ├── unit/              # Unit tests
│   ├── wallet/            # Wallet system tests
│   └── performance/       # Performance tests
│
├── 📁 deployment/          # Production deployment files
├── 📁 docker/             # Docker configuration files
├── 📁 data/               # Data management
│   ├── backups/           # Database backups
│   └── fixtures/          # Test data
├── 📁 logs/               # Application logs
├── 📁 logs_archive/       # Archived logs
└── 📁 env/                # Virtual environment
```

## 🚫 **Prohibited Practices**

### ❌ **Never Place These in Root Directory:**
- Documentation files (*.md except README.md)
- Utility scripts (*.py except manage.py)
- Test files (test_*.py)
- Configuration files (except core Django files)
- Temporary files or backups
- Debug scripts
- Fix scripts
- Analysis reports

### ❌ **Never Create These Directories in Root:**
- `temp/`, `tmp/`, `backup/`
- `old/`, `archive/`, `deprecated/`
- `fixes/`, `patches/`, `updates/`
- `debug/`, `test_files/`

## ✅ **File Placement Rules**

### **Documentation Files (.md)**
- **Project reports**: `docs/project/reports/`
- **Fix documentation**: `docs/solutions/[category]/`
- **System guides**: `docs/system/`
- **Admin guides**: `docs/admin/`
- **User guides**: `docs/user/`
- **API docs**: `docs/api/`

### **Python Scripts (.py)**
- **Debug/development**: `scripts/development/`
- **Maintenance**: `scripts/maintenance/`
- **Utilities**: `scripts/utilities/`
- **Monitoring**: `scripts/monitoring/`
- **Setup**: `scripts/setup/`
- **Admin tools**: `scripts/admin/`

### **Test Files**
- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/`
- **Admin tests**: `tests/admin/`
- **Payment tests**: `tests/payment/`
- **Performance tests**: `tests/performance/`

### **Configuration Files**
- **Docker**: `deployment/` or `docker/`
- **Deployment**: `deployment/`
- **Environment**: Keep in root only if essential

## 📋 **File Naming Conventions**

### **Documentation Files**
- Use UPPERCASE for major documents: `CRITICAL_FIXES_SUMMARY.md`
- Use descriptive names: `admin_panel_betting_updates_fix.md`
- Include category prefix when helpful: `WEBSOCKET_CONNECTION_FIX.md`

### **Script Files**
- Use lowercase with underscores: `fix_balance_precision.py`
- Include purpose in name: `diagnose_websocket_stability.py`
- Use verb-noun pattern: `create_admin.py`, `cleanup_files.py`

### **Test Files**
- Prefix with `test_`: `test_admin_websocket_fix.py`
- Match the component being tested: `test_betting_updates.py`

## 🔄 **Maintenance Procedures**

### **Weekly File Audit**
1. Check root directory for misplaced files
2. Verify all documentation is in `docs/`
3. Ensure all scripts are in `scripts/`
4. Confirm all tests are in `tests/`

### **Before Adding New Files**
1. Determine the correct directory based on file type and purpose
2. Check if similar file already exists
3. Follow naming conventions
4. Update relevant documentation

### **File Movement Protocol**
1. Use `git mv` for version-controlled files
2. Update any references in code or documentation
3. Test that moved files still work correctly
4. Update import statements if necessary

## 🚨 **Emergency Cleanup Procedure**

If root directory becomes cluttered:

1. **Identify file types**:
   ```bash
   ls -la *.md *.py *.txt *.yml *.yaml
   ```

2. **Move documentation**:
   ```bash
   mv *.md docs/project/reports/  # (except README.md)
   ```

3. **Move scripts**:
   ```bash
   mv debug_*.py scripts/development/
   mv fix_*.py scripts/utilities/
   mv test_*.py tests/integration/
   ```

4. **Remove duplicates**:
   ```bash
   # Check for duplicates before removing
   find . -name "docker-compose*.yml" -not -path "./deployment/*"
   ```

## 📊 **Compliance Checklist**

- [ ] Root directory contains only essential files
- [ ] All documentation in appropriate `docs/` subdirectories
- [ ] All scripts in appropriate `scripts/` subdirectories
- [ ] All tests in appropriate `tests/` subdirectories
- [ ] No duplicate configuration files
- [ ] File names follow established conventions
- [ ] No temporary or debug files in root
- [ ] All new files documented in appropriate README files

## 🔗 **Related Documentation**

- [Project Structure](PROJECT_STRUCTURE.md)
- [File Management Guidelines](FILE_MANAGEMENT_GUIDELINES.md)
- [Development Workflow](../system/DEVELOPMENT_WORKFLOW.md)

---

**Last Updated**: 2025-07-22  
**Maintained By**: Project Organization Team  
**Review Schedule**: Monthly

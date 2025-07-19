# File Management Guidelines

## Color Prediction Game - Project Organization Standards

This document establishes clear guidelines for file organization, naming conventions, and project structure maintenance.

## 📁 **Project Structure Overview**

```
WebSocket_Test/
├── 📁 Core Application
│   ├── polling/              # Main Django app
│   ├── server/              # Django project settings  
│   ├── templates/           # HTML templates
│   ├── static/             # CSS, JS, images
│   └── media/              # User uploads
│
├── 📁 Infrastructure  
│   ├── deployment/         # Docker, production configs
│   ├── logs/              # Application logs
│   ├── logs_archive/      # Archived logs
│   └── env/               # Virtual environment
│
├── 📁 Development
│   ├── tests/             # Test files
│   ├── scripts/           # Utility scripts
│   ├── docs/              # Documentation
│   └── data/              # Data management
│
├── 📁 Root Level (Keep Minimal)
│   ├── manage.py          # Django management
│   ├── requirements.txt   # Dependencies
│   ├── README.md          # Project overview
│   └── .gitignore         # Git ignore rules
```

## 🗂️ **Directory Guidelines**

### **Root Directory Rules**
- Keep only essential files
- No utility scripts or temporary files
- No documentation files (use docs/)
- No backup files (use data/backups/)

### **Scripts Organization**
```
scripts/
├── admin/          # Admin management
├── data/           # Data operations  
├── development/    # Dev tools
├── maintenance/    # System maintenance
├── monitoring/     # Health checks
├── setup/          # Initial setup
└── utilities/      # General utilities
```

### **Documentation Structure**
```
docs/
├── admin/          # Admin documentation
├── api/            # API documentation
├── email/          # Email setup guides
├── project/        # Project management
├── solutions/      # Problem solutions
├── system/         # Technical docs
└── user/           # User guides
```

### **Data Management**
```
data/
├── backups/        # Database backups
├── fixtures/       # Test data
└── exports/        # Data exports
```

## 📝 **Naming Conventions**

### **File Naming**
- Use lowercase with underscores: `file_name.py`
- Be descriptive: `fix_payment_system.py` not `fix.py`
- Include purpose: `test_user_authentication.py`
- Avoid generic names: `script1.py`, `temp.py`

### **Directory Naming**
- Use lowercase with underscores or hyphens
- Be descriptive and consistent
- Group related functionality

### **Documentation Files**
- Use UPPERCASE for main docs: `README.md`
- Use descriptive names: `PAYMENT_SYSTEM_GUIDE.md`
- Include category when helpful: `API_SECURITY_REFERENCE.md`

## 🔧 **File Organization Rules**

### **Scripts Placement**
- **Maintenance**: Database fixes, cleanup operations
- **Setup**: Initial configuration, first-time setup
- **Development**: Testing tools, development helpers
- **Utilities**: General-purpose tools
- **Admin**: Admin user management
- **Data**: Data manipulation, test data creation
- **Monitoring**: Health checks, system monitoring

### **Documentation Placement**
- **System**: Technical architecture, APIs
- **Admin**: Admin panel guides
- **User**: End-user documentation
- **Project**: Project management, organization
- **Solutions**: Problem fixes, troubleshooting

### **Static Files**
- **CSS**: Organized by component/feature
- **JavaScript**: Modular, feature-based organization
- **Images**: Categorized by usage (icons, backgrounds, etc.)

## 🚫 **What NOT to Keep in Root**

### **Avoid These in Root Directory**
- ❌ Utility scripts (`cleanup.py`, `fix_*.py`)
- ❌ Documentation files (`GUIDE.md`, `NOTES.md`)
- ❌ Backup files (`db_backup.sqlite3`)
- ❌ Temporary files (`temp_*.py`, `test_*.py`)
- ❌ Configuration backups (`settings_old.py`)

### **Move These to Appropriate Directories**
- 📁 Scripts → `scripts/category/`
- 📁 Docs → `docs/category/`
- 📁 Backups → `data/backups/`
- 📁 Tests → `tests/category/`

## ✅ **Best Practices**

### **Regular Maintenance**
1. **Weekly**: Review root directory for clutter
2. **Monthly**: Organize new scripts and documentation
3. **Quarterly**: Archive old logs and backups
4. **As needed**: Update documentation and guidelines

### **Before Adding New Files**
1. Determine appropriate directory
2. Use descriptive naming
3. Add documentation if needed
4. Update relevant README files

### **Code Organization**
- Group related functionality
- Use consistent naming patterns
- Include proper documentation
- Follow established conventions

## 📋 **Checklist for File Management**

### **New Script Checklist**
- [ ] Descriptive filename
- [ ] Placed in correct scripts/ subdirectory
- [ ] Includes docstring/comments
- [ ] Updated scripts/README.md if needed

### **New Documentation Checklist**
- [ ] Placed in appropriate docs/ subdirectory
- [ ] Uses consistent formatting
- [ ] Updated docs/README.md index
- [ ] Cross-referenced with related docs

### **Root Directory Cleanup Checklist**
- [ ] No utility scripts in root
- [ ] No documentation files in root
- [ ] No backup files in root
- [ ] Only essential project files remain

## 🔄 **Migration Guidelines**

### **Moving Existing Files**
1. Identify file purpose and category
2. Move to appropriate directory
3. Update any references or imports
4. Update documentation
5. Test functionality after move

### **Maintaining References**
- Update import statements in code
- Update documentation links
- Update script execution paths
- Test all affected functionality

This structure ensures maintainable, organized, and scalable project management.

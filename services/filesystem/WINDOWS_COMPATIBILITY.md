# Windows Compatibility Guide

## ✅ Summary

The Eva Filesystem Service is **fully compatible with Windows** with minor setup adjustments.

## 🎯 Tested Functionality

All core features work cross-platform:
- ✅ Path handling (via `pathlib.Path`)
- ✅ File operations (via `aiofiles`)
- ✅ SQLite database
- ✅ BLAKE3 hashing
- ✅ FastAPI/Uvicorn server
- ✅ Authentication & security
- ✅ Audit logging

## ⚠️ Windows-Specific Considerations

### 1. **python-magic Library** (MIME type detection)

**Issue**: `python-magic` requires `libmagic` which is Unix-native.

**Windows Solution**:
```bash
# Instead of: pip install python-magic
# Use the Windows-compatible version:
pip install python-magic-bin
```

The `python-magic-bin` package includes the required DLL for Windows.

**Alternative**: Update `requirements.txt`:
```txt
# Cross-platform MIME detection
python-magic==0.4.27; sys_platform != 'win32'
python-magic-bin==0.4.14; sys_platform == 'win32'
```

### 2. **File Permissions**

**Issue**: Unix permissions (644, 755) don't directly map to Windows ACLs.

**Impact**: Minimal - permissions are stored as metadata but not enforced by the service.

**Current Behavior**:
- Linux/Mac: Returns `"permissions": "644"`
- Windows: Returns Windows permission bits (different format)

**Note**: This is metadata only and doesn't affect service functionality.

### 3. **Symlink Support**

**Issue**: Windows symlinks require:
- Administrator privileges, OR
- Developer Mode enabled (Windows 10+)

**Impact**:
- Symlink detection works on Windows
- If user lacks privileges, symlinks appear as regular files
- Security validation still functions correctly

**Recommendation**:
- Enable Developer Mode on Windows 10+
- Or run service with appropriate privileges if symlink security is critical

### 4. **Path Separators**

**Status**: ✅ No issues - `pathlib.Path` handles this automatically.

Windows paths like `C:\Users\...` work seamlessly.

## 🚀 Windows Setup Instructions

### 1. Install Python 3.10+
```powershell
# Download from python.org or use winget
winget install Python.Python.3.11
```

### 2. Install Dependencies
```powershell
cd services\filesystem
pip install -r requirements.txt

# If python-magic fails, install the Windows version:
pip uninstall python-magic
pip install python-magic-bin
```

### 3. Configure Environment
```powershell
# Copy example config
copy .env.example .env

# Edit .env with Windows paths
# Example:
# ALLOWED_PATHS=C:\Users\YourName\Documents,C:\Projects
# SQLITE_DB_PATH=.\data\filesystem.db
# AUDIT_LOG_PATH=.\data\audit.log
```

### 4. Run the Service
```powershell
# From services/filesystem directory
python -m src.main

# Or with uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8005
```

### 5. Test the Service
```powershell
# Health check
curl http://localhost:8005/health

# List directory (using PowerShell)
Invoke-RestMethod -Uri "http://localhost:8005/mcp/tools/list_directory" `
  -Method POST `
  -Headers @{"Authorization"="Bearer your_read_token"} `
  -ContentType "application/json" `
  -Body '{"path":"C:\\Users\\YourName\\Documents"}'
```

## 🧪 Running Tests on Windows

```powershell
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

## 📝 Configuration Example (Windows)

`.env` file for Windows:
```env
# Security tokens
READ_TOKEN=your_secure_read_token_here
WRITE_TOKEN=your_secure_write_token_here
JWT_SECRET=your_secret_key_here

# Windows paths - use forward slashes or escaped backslashes
ALLOWED_PATHS=C:/Users/YourName/Documents,C:/Projects/Eva
# Or with escaped backslashes:
# ALLOWED_PATHS=C:\\Users\\YourName\\Documents,C:\\Projects\\Eva

MAX_FILE_SIZE_MB=100

# Storage (relative paths work on Windows too)
SQLITE_DB_PATH=./data/filesystem.db
AUDIT_LOG_PATH=./data/audit.log
```

## 🐛 Known Limitations

1. **File permissions metadata**: Different format than Unix (cosmetic only)
2. **Symlink creation**: Requires admin or Developer Mode
3. **python-magic**: Requires `python-magic-bin` package

## ✨ Performance Notes

- **Same performance** on Windows as Linux/Mac
- SQLite is equally efficient
- BLAKE3 hashing uses optimized native code on all platforms

## 🔧 Troubleshooting

### "Could not find magic library"
```powershell
pip uninstall python-magic
pip install python-magic-bin
```

### "Invalid path" errors with backslashes
Use forward slashes in `.env` file:
```env
ALLOWED_PATHS=C:/Users/Name/Documents
```

### Permission denied when creating symlinks
Enable Developer Mode:
1. Settings → Update & Security → For Developers
2. Enable "Developer Mode"

## 🎉 Conclusion

The Eva Filesystem Service is **production-ready for Windows** with the simple adjustment of using `python-magic-bin` instead of `python-magic`. All core security features, indexing, and MCP tools work identically across platforms.

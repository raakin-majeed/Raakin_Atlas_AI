try:
    from sqlalchemy.ext.asyncio import AsyncSession
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")

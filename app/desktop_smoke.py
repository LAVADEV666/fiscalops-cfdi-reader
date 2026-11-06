"""Compatibility launcher for the SPEC011 desktop container."""
import sys


def main():
    if '--check' in sys.argv:
        from scripts.spec011.check_environment import inspect
        import json
        result=inspect()
        print(json.dumps(result,indent=2))
        return 0 if result['status']=='AVAILABLE' else 3
    from app.desktop.main import main as launch
    return launch()


if __name__=='__main__':
    raise SystemExit(main())
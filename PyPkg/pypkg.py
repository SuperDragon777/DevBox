import sys
import subprocess
import os

def ensure_pip():
    try:
        subprocess.run([sys.executable, '-m', 'pip', '--version'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        try:
            import ensurepip
            ensurepip.bootstrap()
            return True
        except Exception:
            try:
                import urllib.request
                url = 'https://bootstrap.pypa.io/get-pip.py'
                urllib.request.urlretrieve(url, 'get-pip.py')
                subprocess.run([sys.executable, 'get-pip.py'], check=True)
                os.remove('get-pip.py')
                return True
            except Exception:
                return False

def install_package(package_name):
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', package_name], check=True)
        print(f"Package {package_name} installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {package_name}: {e}")

def list_packages():
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error listing packages: {e}")

def uninstall_package(package_name):
    try:
        confirm = input(f"Are you sure you want to uninstall {package_name}? (y/n): ").strip().lower()
        if confirm == 'y':
            subprocess.run([sys.executable, '-m', 'pip', 'uninstall', package_name, '-y'], check=True)
            print(f"Package {package_name} uninstalled.")
        else:
            print("Uninstallation cancelled.")
    except subprocess.CalledProcessError as e:
        print(f"Error uninstalling {package_name}: {e}")

def main():
    if not ensure_pip():
        print("Failed to set up pip. Exiting.")
        return

    while True:
        print("\nMenu:")
        print("1. Install a package")
        print("2. List installed packages")
        print("3. Uninstall a package")
        print("4. Exit")
        choice = input("Choose an action (1-4): ").strip()

        if choice == '1':
            package = input("Enter package name to install: ").strip()
            if package:
                install_package(package)
            else:
                print("Package name cannot be empty.")
        elif choice == '2':
            list_packages()
        elif choice == '3':
            package = input("Enter package name to uninstall: ").strip()
            if package:
                uninstall_package(package)
            else:
                print("Package name cannot be empty.")
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please enter a number from 1 to 4.")

if __name__ == "__main__":
    main()

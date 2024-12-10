import pkg_resources

installed_packages = pkg_resources.working_set
packages = sorted([(d.project_name, d.version) for d in installed_packages])

for package_name, version in packages:
    print(f"{package_name}: {version}")
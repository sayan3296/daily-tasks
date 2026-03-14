#!/bin/bash

# 1. Read the current version directly from the .spec file
CURRENT_VERSION=$(grep '^Version:' daily-tasks.spec | awk '{print $2}')

# 2. Split the version into Major and Minor (e.g., "1.0" becomes MAJOR="1", MINOR="0")
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)

# 3. Increment the Minor version
NEW_MINOR=$((MINOR + 1))
VERSION="${MAJOR}.${NEW_MINOR}"

echo "⬆️  Auto-bumping version from ${CURRENT_VERSION} to ${VERSION}..."

# 4. Automatically update the .spec file with the new version using 'sed'
# This also resets the Release number back to 1 for the new version
sed -i "s/^Version:.*/Version:        ${VERSION}/" daily-tasks.spec
sed -i "s/^Release:.*/Release:        1/" daily-tasks.spec

echo "🚀 Starting Daily-Tasks RPM Build Process for v${VERSION}..."

# Ensure the RPM build folders exist
rpmdev-setuptree

# Package the source code into a tarball
echo "📦 Packaging source files..."
mkdir -p daily-tasks-${VERSION}
cp app.py daemon.py icon.png daily-tasks-${VERSION}/
tar -czf ~/rpmbuild/SOURCES/daily-tasks-${VERSION}.tar.gz daily-tasks-${VERSION}/
rm -rf daily-tasks-${VERSION}

# Copy the desktop shortcuts and spec file to the build environment
cp dailytasks.desktop dailytasks-daemon.desktop ~/rpmbuild/SOURCES/
cp daily-tasks.spec ~/rpmbuild/SPECS/

# Build the RPM!
echo "⚙️  Building the RPM..."
rpmbuild -ba ~/rpmbuild/SPECS/daily-tasks.spec

echo "✅ Success! Your new RPM is ready in: ~/rpmbuild/RPMS/noarch/"

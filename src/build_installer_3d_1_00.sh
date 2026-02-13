#!/bin/bash

################################################################################
# OpenStrandStudio 3D macOS PKG Installer Builder - Version 1.00
# Date: Created February 13, 2026
#
# LOGIC EXPLANATION:
# ==================
# This script creates a macOS .pkg installer for OpenStrandStudio 3D.
# English only for this version.
#
# BUILD PROCESS:
# --------------
# 1. Creates temporary directories for scripts and resources
# 2. Generates postinstall script (creates desktop icon, offers to launch app)
# 3. Creates Distribution.xml (installer configuration)
# 4. Creates welcome.html and license.html (English only)
# 5. Builds component package with pkgbuild
# 6. Builds final product package with productbuild
# 7. Cleans up temporary files
################################################################################

# Set variables
APP_NAME="OpenStrand Studio 3D"
VERSION="1.00"
APP_DATE="13_February_2026"
PUBLISHER="Yonatan Setbon"
IDENTIFIER="com.yonatan.openstrandstudio3d"

# Create directories
WORKING_DIR="$(mktemp -d)"
SCRIPTS_DIR="$WORKING_DIR/scripts"
RESOURCES_DIR="$WORKING_DIR/resources"
PKG_PATH="/Users/yonatan/Documents/GitHub/OpenStrandStudio3d/src/installer_output/${APP_NAME}_${VERSION}.pkg"

mkdir -p "$SCRIPTS_DIR" "$RESOURCES_DIR"

# Create postinstall script
cat > "$SCRIPTS_DIR/postinstall" << 'EOF'
#!/bin/bash

# Get the user's home directory
USER_HOME=$HOME

# Create Desktop icon
cp -f "/Applications/OpenStrandStudio 3D.app/Contents/Resources/openstrandstudio3d_icon.icns" "$USER_HOME/Desktop/OpenStrandStudio3D.icns"

# Create Launch Agent for auto-start (optional)
LAUNCH_AGENT_DIR="$USER_HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENT_DIR"

# Ensure all dependencies are properly accessible
if [ -d "/Applications/OpenStrandStudio 3D.app/Contents/Resources/lib/python3.9/site-packages" ]; then
    chmod -R 755 "/Applications/OpenStrandStudio 3D.app/Contents/Resources/lib/python3.9/site-packages"
fi

# Ask if user wants to launch the app now
osascript <<EOD
    tell application "System Events"
        activate
        set launch_now to button returned of (display dialog "Installation Complete! Would you like to launch OpenStrandStudio 3D now?" buttons {"Launch Now", "Later"} default button "Launch Now")
        if launch_now is "Launch Now" then
            tell application "OpenStrandStudio3D" to activate
        end if
    end tell
EOD

exit 0
EOF

# Make postinstall script executable
chmod +x "$SCRIPTS_DIR/postinstall"

# Create Distribution.xml
cat > "$WORKING_DIR/Distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>$APP_NAME $VERSION</title>
    <organization>$PUBLISHER</organization>
    <domains enable_localSystem="true"/>
    <options customize="allow" require-scripts="true" allow-external-scripts="no"/>
    <welcome file="welcome.html"/>
    <license file="license.html"/>
    <choices-outline>
        <line choice="default">
            <line choice="com.yonatan.openstrandstudio3d"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="com.yonatan.openstrandstudio3d" visible="false">
        <pkg-ref id="com.yonatan.openstrandstudio3d"/>
    </choice>
    <pkg-ref id="com.yonatan.openstrandstudio3d" version="$VERSION" onConclusion="none">OpenStrandStudio3D.pkg</pkg-ref>
</installer-gui-script>
EOF

# Create welcome.html (English only)
cat > "$RESOURCES_DIR/welcome.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body>
    <h2>Welcome to OpenStrandStudio 3D 1.00</h2>
    <p>This will install OpenStrandStudio 3D on your computer. You will be guided through the steps necessary to install this software.</p>
    <p>OpenStrandStudio 3D is a 3D strand/braid design application using OpenGL.</p>
    <p>The program is brought to you by Yonatan Setbon. You can contact me at ysetbon@gmail.com.</p>
</body>
</html>
EOF

# Create license.html
cat > "$RESOURCES_DIR/license.html" << EOF
<!DOCTYPE html>
<html>
<body>
    <h2>License Agreement</h2>
    <p>Copyright (c) 2026 $PUBLISHER</p>
    <p>By installing this software, you agree to the terms and conditions.</p>
</body>
</html>
EOF

# Build component package
echo "Building component package..."
pkgbuild \
    --root "/Users/yonatan/Documents/GitHub/OpenStrandStudio3d/src/dist/OpenStrandStudio3D.app" \
    --install-location "/Applications/OpenStrandStudio 3D.app" \
    --scripts "$SCRIPTS_DIR" \
    --identifier "$IDENTIFIER" \
    --version "$VERSION" \
    "$WORKING_DIR/OpenStrandStudio3D.pkg"

if [ ! -f "$WORKING_DIR/OpenStrandStudio3D.pkg" ]; then
    echo "Error: Failed to create component package"
    exit 1
fi

# Build product package
echo "Building product package..."
productbuild \
    --distribution "$WORKING_DIR/Distribution.xml" \
    --resources "$RESOURCES_DIR" \
    --package-path "$WORKING_DIR" \
    "$PKG_PATH"

if [ ! -f "$PKG_PATH" ]; then
    echo "Error: Failed to create product package"
    exit 1
fi

# Sign the package (optional - requires Developer ID)
# productbuild --sign "Developer ID Installer: Your Name (XXXXXXXXXX)" "$PKG_PATH" "$PKG_PATH.signed"
# mv "$PKG_PATH.signed" "$PKG_PATH"

# Verify the package
echo "Verifying package..."
pkgutil --check-signature "$PKG_PATH" 2>/dev/null || echo "Package is unsigned (normal for development)"

# Clean up
rm -rf "$WORKING_DIR"

echo "Package created successfully at: $PKG_PATH"
echo "Version: $VERSION"
echo "Publisher: $PUBLISHER"

# Test the installer
echo "To test the installer, run:"
echo "sudo installer -pkg \"$PKG_PATH\" -target /"

# Open the installer_output directory
open "$(dirname "$PKG_PATH")"

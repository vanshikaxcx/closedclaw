#!/bin/bash

# Script to rename MunimAI to Arthsetu Merchant Help throughout documentation
# This preserves API endpoints and code structure while updating user-facing text

echo "Renaming MunimAI to Arthsetu Merchant Help in documentation..."

# Update markdown documentation files
find ../. -name "*.md" -type f -exec sed -i '' 's/MunimAI/Arthsetu Merchant Help/g' {} \;
find ../. -name "*.md" -type f -exec sed -i '' 's/Munim AI/Arthsetu Merchant Help/g' {} \;

echo "✅ Documentation updated!"
echo "Note: API endpoints remain unchanged for backward compatibility"

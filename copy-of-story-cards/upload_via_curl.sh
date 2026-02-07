#!/bin/bash
# Upload persona images to MinIO using curl

MINIO_HOST="localhost:9000"
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="MIn!o_pASS_vitte2006_&&_pic\$"
BUCKET="vitte-bot"
FOLDER="persona-dialogs"

# Base directory
IMAGES_DIR="cropped_736x414"

# Array of files and their persona keys
declare -A FILES=(
    ["Stacey - Вечер на крыше и закат вдвоём.jpg"]="stacey"
    ["Mei - Встреча в торговом центре.png"]="mei"
    ["Yuna - Первый вечер и мягкая беседа.jpg"]="yuna"
    ["Taya - Служебный выход бара.png"]="taya"
    ["Julie - Репетитор на дому.png"]="julie"
    ["Ash - В гостиной.png"]="ash"
    ["Lina - Прятки в сауне.png"]="lina"
    ["Marianna - Ночное эхо.png"]="marianna"
)

echo "🚀 Starting upload to MinIO..."
echo ""

for filename in "${!FILES[@]}"; do
    persona_key="${FILES[$filename]}"
    filepath="$IMAGES_DIR/$filename"

    # Get file extension
    ext="${filename##*.}"

    # Object name in MinIO
    object_name="$FOLDER/$persona_key.$ext"

    if [ ! -f "$filepath" ]; then
        echo "⚠️  File not found: $filepath"
        continue
    fi

    # Upload using MinIO API (S3-compatible)
    # Using simple PUT request
    date_value=$(date -R)

    curl -X PUT \
        -H "Host: $MINIO_HOST" \
        -H "Date: $date_value" \
        -T "$filepath" \
        "http://$MINIO_HOST/$BUCKET/$object_name" \
        2>&1 | grep -v "progress"

    if [ $? -eq 0 ]; then
        echo "✅ Uploaded: $persona_key.$ext"
    else
        echo "❌ Failed: $persona_key.$ext"
    fi
done

echo ""
echo "🎉 Upload complete!"
echo "Images accessible at: https://craveme.tech/storage/$FOLDER/{persona_key}.{ext}"

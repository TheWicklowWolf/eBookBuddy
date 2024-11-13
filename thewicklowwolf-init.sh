#!/bin/sh

echo -e "\033[1;32mTheWicklowWolf\033[0m"
echo -e "\033[1;34meBookBuddy\033[0m"
echo "Initializing app..."

cat << 'EOF'
_____________________________________

               .-'''''-.             
             .'         `.           
            :             :          
           :               :         
           :      _/|      :         
            :   =/_/      :          
             `._/ |     .'           
          (   /  ,|...-'             
           \_/^\/||__                
       _/~  `""~`"` \_               
     __/  -'/  `-._ `\_\__           
    /    /-'`  `\   \  \-.\          
_____________________________________
Brought to you by TheWicklowWolf   
_____________________________________

If you'd like to buy me a coffee:
https://buymeacoffee.com/thewicklow

EOF

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "-----------------"
echo -e "\033[1mRunning with:\033[0m"
echo "PUID=${PUID}"
echo "PGID=${PGID}"
echo "-----------------"

# Create the required directories with the correct permissions
echo "Setting up directories.."
mkdir -p /ebookbuddy/config /ebookbuddy/.wdm
chown -R ${PUID}:${PGID} /ebookbuddy

# Start the application with the specified user permissions
echo "Running eBookBuddy..."
exec su-exec ${PUID}:${PGID} gunicorn src.eBookBuddy:app -c gunicorn_config.py

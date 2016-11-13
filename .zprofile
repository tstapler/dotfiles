if hash keychain 2>/dev/null; then
	eval `keychain --agents ssh --eval id_rsa`
fi

#!/usr/bin/awk -f 
BEGIN {
	variable="";
}
/^In / {
	variable=$2;
}
/on line/{
	print variable":"$0;
}

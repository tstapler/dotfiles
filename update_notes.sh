#!/usr/bin/env bash

set -o nounset                              # Treat unset variables as an error

__ScriptVersion="0.0.1"

#===  FUNCTION  ================================================================
#         NAME:  usage
#  DESCRIPTION:  Display usage information.
#===============================================================================
usage ()
{
  echo "Usage :  $0 [options] [ZIP_GLOB]
  Unarchive a zipfile full of pdfs into the current directory

    Options:
    -h|help       Display this message
    -v|version    Display script version"

}    # ----------  end of function usage  ----------

#-----------------------------------------------------------------------
#  Handle command line arguments
#-----------------------------------------------------------------------

while getopts ":hv" opt
do
  case $opt in

  h|help     )  usage; exit 0   ;;

  v|version  )  echo "$0 -- Version $__ScriptVersion"; exit 0   ;;

  * )  echo -e "\n  Option does not exist : $OPTARG\n"
      usage; exit 1   ;;

  esac    # --- end of case ---
done
shift $(($OPTIND-1))

GLOB="${1:-CPRE}" 

# Unzip and flatten zipfile
find . -maxdepth 1 -iname \*"${GLOB}"\*.zip \
  -exec unzip -jn {} \; \
  -exec rm -f {} \; 
  
# Add notes that aren't in git annex
find . -maxdepth 1 -type f -name \*"${GLOB}"\*.pdf | xargs -r git annex add

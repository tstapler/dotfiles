#-------------------------BASH_UTILS---------------------------------
#author=Tyler Stapler
#This is a file to store snippets of bash that have come in handy from one point to another
#I believe that keeping a record will help remind me of the uses for various utilities 


#--Batch Rename--
#This script uses cp, ls, and sed to rename User Program Displays in a higher range
#
#We first take all of the files starting with a number and pipe them into sed
#EG: 2-Setup 68.dsp
#
#Next we use sed to find the number 68 and increment it by 4 we then copy the 
#file to is new name using the bash utility cp (copy)
#EG: 2-Setup 68.dsp -> 2-Setup 72.dsp
#
#Several things to note:
#The sed -r flag enables enhanced regular expressions
#g and e are flags to sed's substitute command
#g will replace all matches of the  regex instead of just the first
#e pipes input from a shell command into a pattern space. This will execute whatever command
#is found in the pattern space and return its output

$ ls [[:digit:]]* | sed -r 's/(.*)( [1-9]+)(.*)/cp -v "\0" "\1$((/2_4))\3"/ge'

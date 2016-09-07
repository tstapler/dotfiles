#!/usr/bin/python
import fileinput
import re
import collections

ErrorMessage = collections.namedtuple('ErrorMessage', ['file', 'srcline',
                                                       'destline', 'message'])

file_re = re.compile(r'--- (.*\.py)')
range_re = re.compile(r'@@ -(.*),\d+ \+')


def main():
    file = ""
    line_number = 1

    messages = []

    src = {}

    dest = {}

    for line in fileinput.input():
        if line.startswith(" "):
            line_number += 1
        elif line.startswith("---"):
            file = file_re.match(line).group(1)
            continue
        elif line.startswith("+++"):
            continue
        elif line.startswith("@@"):
            line_number = int(range_re.match(line).group(1))
        elif line.startswith("+"):
            content = line[1:].rstrip('\n')
            if content in src:
                messages.append(ErrorMessage(file, src[content],
                                             line_number, content))
                del src[content]
            else:
                dest[content] = line_number
            line_number += 1
            continue
        elif line.startswith("-"):
            content = line[1:].rstrip('\n')
            if content in dest:
                messages.append(ErrorMessage(file, line_number,
                                             dest[content], content))
                del dest[content]
            else:
                src[content] = line_number
            line_number += 1
            continue
        else:
            pass

    for msg in messages:
        print("{}:Import '{}' should be moved from line {} to line {}".format(msg.file, msg.message, msg.srcline, msg.destline))

if __name__ == '__main__':
    main()

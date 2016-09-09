#!/usr/bin/python
import fileinput
import re
import collections

ErrorMessage = collections.namedtuple('ErrorMessage', ['file', 'srcline',
                                                       'destline', 'message'])

file_re = re.compile(r'--- (.*\.py)')
range_re = re.compile(r'@@ -(.*),\d+ \+(.*),')


def main():
    file = ""
    old_number = 1
    new_number = 1

    messages = []

    src = {}

    dest = {}

    for line in fileinput.input():
        if line.startswith(" "):
            old_number += 1
            new_number += 1
        elif line.startswith("---"):
            file = file_re.match(line).group(1)
            continue
        elif line.startswith("+++"):
            continue
        elif line.startswith("@@"):
            old_number = int(range_re.match(line).group(1))
            new_number = int(range_re.match(line).group(2))
        elif line.startswith("+"):
            content = line[1:].rstrip('\n')
            if content in src:
                messages.append(ErrorMessage(file, src[content],
                                             new_number, content))
                del src[content]
            elif content == "":
                messages.append(ErrorMessage(file, None,
                                             new_number, "Add a line"))
            else:
                dest[content] = new_number
            new_number += 1
        elif line.startswith("-"):
            content = line[1:].rstrip('\n')
            if content in dest:
                messages.append(ErrorMessage(file, old_number,
                                             dest[content], content))
                del dest[content]
            elif content == "":
                messages.append(ErrorMessage(file, old_number,
                                             None, "Remove a line"))
            else:
                src[content] = old_number
            old_number += 1
        else:
            pass

    for msg in messages:
        if not msg.srcline:
            print('{file}:{line}:{msg}'
                  .format(file=msg.file, line=msg.destline, msg=msg.message))
        elif not msg.destline:
            print('{file}:{line}:{msg}'
                  .format(file=msg.file, line=msg.srcline, msg=msg.message))
        else:
            print('{}:{}:Import statement "{}" should be moved from the '
                  'old line {} to the new line {}'
                  .format(msg.file, msg.srcline, msg.message,
                          msg.srcline, msg.destline))

if __name__ == '__main__':
    main()

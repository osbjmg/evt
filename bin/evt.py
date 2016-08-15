#!/usr/bin/python
# -* coding: UTF-8 -*-
#import iso8602
import pprint
import cgi
import cgitb
import json
from slackclient import SlackClient
import datetime
import pytz
import re
import os

cgitbLogDir = os.environ.get('SLACKBOTS_J3B_CGI_LOGDIR')
cgitb.enable(display=0, logdir=cgitbLogDir, format='text') # display=1 if we want to print errors, they will log to cgitbLogDir always though

try :
    EXPECTED_TOKEN = os.environ.get('SLACKBOTS_J3B_TOKEN') # token for eve /evt command
    EXPECTED_TEAM_ID = os.environ.get('SLACKBOTS_J3B_TEAM') # team ID eve /evt command
    BOT_ID = os.environ.get('SLACKBOTS_J3B_BOTID') # time helper bot ID for eve, j3b
    BOT_TOKEN = os.environ.get('SLACKBOTS_J3B_BOT_TOKEN') # time helper bot token for j3b
except KeyError:
    print 'One or more environment variables are not properly set.'
    sys.exit(1)

slack_client = SlackClient(BOT_TOKEN)

def getUserTimezone(user) :
    api_call = slack_client.api_call("users.info", user=user)
    if api_call.get('ok'):
        profile = api_call.get('user')
        name = profile['name']
        if profile['tz'] :
            tz = profile['tz']
        else :
            tz = None
        tz_label = profile['tz_label']
        tz_offset_sec = profile['tz_offset']
        # testnow = some time to represent a time between DST in EMEA and the US
        now = datetime.datetime.now(tz=pytz.utc) # tz "aware"
    return tz, tz_label, tz_offset_sec, now, name

def handle_command(command, channel, user) :
    # basic options
    #  help
    #  provide desired time hh:mm, hh, hhmm, optional timezone override if none upon lookup
    #    spit back current and future local time
    #    spit back hh:mm until that time
    #  provide offset in hh:mm, or dd:hh:mm, russian NN-NN from now
    #  check timezone  - /time --mytz
    #  debug/verbose to check inputs and maybe allow all options, or not?
    #  option: private/direct message quiet/silent
    #  option: time until dt

    # use str replacement %s
    # find libs for time and isdst()
    # note mil time

    """
    1 non arg just now
    2 next time in the future in my tz ( if no tz, say so and gib utc)
    3 next time in future in a specific offset
    4 some hh:mm in the future (even day)
    5 help

    important: option to show the DST boundary dates in different TZs and current DST status

    silent option
    """
    wallClockTime = None

    now_strings = { '--now', 'now', '-n'}
    help_strings = {'--help', 'help', 'halp', '-h'}
    verbose_strings = {'-v', '--verbose', 'verbose'}
    offset_strings = {'-o', '--offset'}
    tz_specified_strings = {'-tz', '--timezone', 'tz'}
    check_mytz_strings = {'--mytz', '--sme','--check', '-c'}

    if command :
        # regex to match 200, 0300, 11:00, 16-18 time formats.
        requestedTime = re.compile('.*?([0-9]{1,2}[:\-\.]*[0-9]{2})') # explain: match anything, 0 or more times [non-greedy], return one or two numbers, 0 or more dividers [: or -], another 2 numbers.
        for cmd in command :
            if re.match(requestedTime, cmd) :
                wallClockTime = re.match(requestedTime, cmd).group(1)


    # no input, give current time
    if (command is None or ((command is not None) and (set(command).intersection(now_strings)))):
        tz_city, tz, offset, now, name = getUserTimezone(user)
        response_type = 'in_channel'
        mainText = 'Current EVE Time: '+ str(now.strftime("*%H:%M*   %Y-%m-%d"))
        if tz_city is not None:
            attachmentText = name + "'s time: " + now.astimezone(pytz.timezone(tz_city)).strftime("%H:%M | %I:%M %p   %Y-%m-%d") + '  (UTC' + str(offset/60/60) + '/' + tz + ')'
        else : # some users do not have a tz in slack, but usually have the tz_label and offset, here I have to trust slack converted properly
            attachmentText = name + "'s time: " + (now + datetime.timedelta(seconds=offset)).strftime("%H:%M | %I:%M %p   %Y-%m-%d") + '  (UTC' + str(offset/60/60) + '/' + tz + ')'

    # consider making these all function calls in the event we need to break?
    elif wallClockTime is not None: # a time is given, let's determine time until EVT (no date assumes next time we hit this time on the clock)
        # first, create a time string
        timeString = ''
        timeValid = True
        threeOrFourDigits = re.compile('^([0-9]{1,2})[:\-\.]*([0-9]{2})')
        outputList = re.findall(threeOrFourDigits, wallClockTime)
        for item in outputList :
            for stringInTuple in item :
                timeString += stringInTuple
        # validate time string
        if len(timeString) == 4 :
            hours = timeString[0:2]
            minutes = timeString[2:]
        elif len(timeString) == 3 :
            hours = timeString[0]
            minutes = timeString[1:]

        if not (0 <= int(hours) <= 23) :
            timeValid = False
        if not ( 0 <= int(minutes) <= 59 ) :
            timeValid = False

        # convert time
        # present time in a nifty manner, left/right eve time, your time, difference, colors
        #  see elephants formatting, color
        tz_city, tz, offset, now, name = getUserTimezone(user)
        response_type = 'in_channel'
        if timeValid is True :
            mainText = '_*BETA FEATURE UNDER CONSTRUCTION*_\nRequested time is: '+ hours + ':' + minutes + ' EVE Time'
        else :
            mainText = 'Error: requested an invalid EVE time (' + hours + ':' + minutes + ')'
        if tz_city is not None:
            attachmentText = name + "'s time: " + now.astimezone(pytz.timezone(tz_city)).strftime("%H:%M | %I:%M %p   %Y-%m-%d") + '  (UTC' + str(offset/60/60) + '/' + tz + ')'
        else : # some users do not have a tz in slack, but usually have the tz_label and offset, here I have to trust slack converted properly
            attachmentText = name + "'s time: " + (now + datetime.timedelta(seconds=offset)).strftime("%H:%M | %I:%M %p   %Y-%m-%d") + '  (UTC' + str(offset/60/60) + '/' + tz + ')'

    # verbose, debug and give current time OR try to determine if we are doing another variant
    elif set(command).intersection(verbose_strings) :
        tz_city, tz, offset, now, name = getUserTimezone(user)
        response_type = 'ephemeral'
        mainText = 'Current EVE Time: '+ str(now.strftime("*%H:%M*    %Y-%m-%d")) + '\n' \
        + 'tz_city: ' + tz_city + '\n' \
        + 'tz: ' + tz + '\n' \
        + 'offset: ' + str(offset) + '\n' \
        + 'now(iso): ' + str(now.isoformat())
        #+ 'name: ' + str(name) + '\n'
        attachmentText = 'attachmentText + now.astimezone(pytz.timezone(tz_city)).strftime(%H:%M (UTC+str(offset/60/60)    %Y-%m-%d)' \
        + now.astimezone(pytz.timezone(tz_city)).strftime("%H:%M (UTC"+str(offset/60/60)+")" +  "    %Y-%m-%d")

    # check user timezone
    elif set(command).intersection(check_mytz_strings) :
        tz_city, tz, offset, usersTime, name = getUserTimezone(user)
        response_type = 'in_channel'
        mainText = 'Slack-provided user Timezone info\n'
        if tz_city is not None :
            attachmentText = 'user: ' + name + '\n' \
            + 'location: ' + tz_city + '\n' \
            + 'timezone: ' + tz + '\n' \
            + 'offset: ' + str(offset) +' seconds / ' + str(offset/60/60) + ' hours'
        else :
            attachmentText = 'user: ' + name + '\n' \
            + 'location: None \n' \
            + 'timezone: ' + tz + '\n' \
            + 'offset: ' + str(offset) +' seconds / ' + str(offset/60/60) + ' hours'

    # help, print usage
    else :
        #elif set(command).intersection(help_strings) :
        response_type = 'ephemeral'
        mainText = '_*EveTime Converter Help*_ \n\n' \
        'usage: /evt \n' \
        '             /evt {hhmm|hh:mm|hh-mm} \n' \
        '             /evt {-h|--help} \n' \
        '             /evt something \n\n' \
        '               -c, --civilian       Not military time\n' \
        '               -o, --offset         Offset +/- Eve time\n'
        attachmentText = ''
        #attachmentText = 'Usage:/evt [hhmm|hh:mm|hh-mm] \n' \

    response = {
        'response_type': response_type,
        'text': mainText,
        'attachments': [{'text': attachmentText
        }]
    }

    print(json.dumps(response))

if __name__ == "__main__" :
    #print('Content-Type: text/html;charset=utf-8')
    #print('Content-Type: text/plain;charset=utf-8')
    print('Content-Type: application/json')
    print #newline for HTTP headers
    form = cgi.FieldStorage()
    if form.getfirst('token', '') != EXPECTED_TOKEN or form.getfirst('team_id', '') != EXPECTED_TEAM_ID :
        print('')
        print('')
        print('')
        print('')
        print('     #----------------------------------------------------------#')
        print('     #                                                          #')
        print('     #     Error:                                               #')
        print('     #     Invalid or missing token/team_id in POST data.       #')
        print('     #                                                          #')
        print('     #                                                          #')
        print('     #----------------------------------------------------------#')
        exit()

    if form.getfirst('text') :
        commandArgs = form.getfirst('text').split()
    else :
        commandArgs = None
    channel = form.getfirst('channel_name', '')
    user = form.getfirst('user_id', '')
    #tzone = getUserTimezone(user)
    handle_command(commandArgs, channel, user)
    #handle_command(command, channel, user, tzone)

"""
Random notes and crap below:



One way to get values
print('User: '+ form['user_name'].value)
print('Channel: ' + form['channel_name'].value)
print('Typed: ' + form['command'].value + ' ' + form['text'].value)

Ideal format for replies
{
    "response_type": "in_channel",
    "text": "It's 80 degrees right now.",
    "attachments": [
        {
            "text":"Partly cloudy today and tomorrow"
        }
    ]
}
"""

"""
formats:
=========
 GMT-0500 (CDT)

 http://pytz.sourceforge.net/
 https://julien.danjou.info/blog/2015/python-and-timezones
 https://docs.python.org/2/library/time.html

>>> now = datetime.datetime.now(tz=pytz.timezone('US/Eastern'))

>>> now
datetime.datetime(2016, 7, 25, 16, 14, 25, 481934, tzinfo=<DstTzInfo 'US/Eastern' EDT-1 day, 20:00:00 DST>)
>>> nowutc
datetime.datetime(2016, 7, 25, 19, 57, 13, 461040, tzinfo=<UTC>)

>>> now.dst()
datetime.timedelta(0, 3600)
>>> nowutc.dst()
datetime.timedelta(0)


>>> deltatime = datetime.timedelta(seconds=-14400)
>>> print deltatime
-1 day, 20:00:00
>>> print thetime
2016-07-26 15:05:06.934539+00:00
>>> print thetime - deltatime
2016-07-26 19:05:06.934539+00:00

"""
"""
Usage examples:
================

admin@somebox:~$ netstat -h
usage: netstat [-vWeenNcCF] [<Af>] -r
       netstat {-V|--version|-h|--help}
       netstat [-vWnNcaeol] [<Socket> ...]
       netstat { [-vWeenNac] -i | [-cnNe] -M | -s [-6tuw] }

        -r, --route              display routing table
        -i, --interfaces         display interface table
        -g, --groups             display multicast group memberships
        -s, --statistics         display networking statistics (like SNMP)
        -M, --masquerade         display masqueraded connections

        -v, --verbose            be verbose
        -W, --wide               don't truncate IP addresses
        -n, --numeric            don't resolve names
        --numeric-hosts          don't resolve host names
        --numeric-ports          don't resolve port names
        --numeric-users          don't resolve user names
        -N, --symbolic           resolve hardware names
        -e, --extend             display other/more information
        -p, --programs           display PID/Program name for sockets
        -o, --timers             display timers
        -c, --continuous         continuous listing

        -l, --listening          display listening server sockets
        -a, --all                display all sockets (default: connected)
        -F, --fib                display Forwarding Information Base (default)
        -C, --cache              display routing cache instead of FIB

  <Socket>={-t|--tcp} {-u|--udp} {-U|--udplite} {-S|--sctp} {-w|--raw}
           {-x|--unix} --ax25 --ipx --netrom
  <AF>=Use '-6|-4' or '-A <af>' or '--<af>'; default: inet
  List of possible address families (which support routing):
    inet (DARPA Internet) inet6 (IPv6) ax25 (AMPR AX.25)
    netrom (AMPR NET/ROM) ipx (Novell IPX) ddp (Appletalk DDP)
    x25 (CCITT X.25)
"""
"""
msg formatting try
https://api.slack.com/docs/messages/builder?msg={"attachments"%3A[{"title"%3A"Title"%2C"pretext"%3A"Pretext%20_supports_%20mrkdwn"%2C"text"%3A"Testing%20*right%20now!*"%2C"mrkdwn_in"%3A["text"%2C"pretext"]}]}
"""

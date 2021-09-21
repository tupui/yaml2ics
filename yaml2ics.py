import yaml
import sys
import os
from datetime import datetime

import ics
import dateutil
import dateutil.rrule



if len(sys.argv) < 2:
    print('Usage: yaml2ics.py FILE1.yaml FILE2.yaml ...')
    sys.exit(-1)

files = sys.argv[1:]
for f in files:
    if not os.path.isfile(f):
        print(f'Error: {f} is not a file')
        sys.exit(-1)


interval_type = {
    'seconds': dateutil.rrule.SECONDLY,
    'minutes': dateutil.rrule.MINUTELY,
    'hours': dateutil.rrule.HOURLY,
    'days': dateutil.rrule.DAILY,
    'weeks': dateutil.rrule.WEEKLY,
    'months': dateutil.rrule.MONTHLY,
    'years': dateutil.rrule.YEARLY
}

def event_from_yaml(event_yaml):
    d = event_yaml
    repeat = d.pop('repeat', None)

    # See https://icspy.readthedocs.io/en/stable/api.html#event
    #
    # Keywords:
    # name, begin, end, duration, uid, description, created, last_modified,
    # location, url, transparent, alarms, attendees, categories, status,
    # organizer, geo, classification
    event = ics.Event(**d)

    # Handle all-day events
    if not ('duration' in d or 'end' in d):
        event.make_all_day()

    if repeat:
        interval = repeat['interval']

        if not len(interval) == 1:
            print('Error: interval must specify seconds, minutes, hours, days, weeks, months, or years only')
            sys.exit(-1)

        interval_measure = list(interval.keys())[0]
        if not interval_measure in interval_type:
            print('Error: expected interval to be specified in seconds, minutes, hours, days, weeks, months, or years only')
            sys.exit(-1)

        if not 'until' in repeat:
            print('Error: must specify end date for repeating events')
            sys.exit(-1)

        event.end = d.get('end', d['begin'])

        rrule = dateutil.rrule.rrule(
            freq=interval_type[interval_measure],
            until=repeat.get('until'),
            dtstart=d['begin']
        )

        rrule_lines = str(rrule).split('\n')
        rrule_dtstart = [l for l in rrule_lines if l.startswith('DTSTART')][0]
        rrule_dtstart = rrule_dtstart + 'Z'
        rrule_rrule = [l for l in rrule_lines if l.startswith('RRULE')][0]

        event_lines = str(event).split('\r\n')

        # Splice in the rrule
        out = []
        for line in event_lines:
            out.append(line)

            if line.startswith('DTEND'):
                out.append(rrule_rrule + 'Z')
    else:
        out = str(event).split('\r\n')

    now_utc = datetime.utcnow()
    utc_stamp = now_utc.isoformat(
        timespec='seconds'
    ).replace('-', '').replace(':', '') + 'Z'
    out.insert(-1, f'DTSTAMP:{utc_stamp}')

    return '\r\n'.join(out)


def calendar_from_yaml(calendar_yaml):
    cal = ics.Calendar()
    for event in calendar_yaml['events']:
        cal.events.add(event_from_yaml(event))
    return cal


out = []
for f in files:
    calendar_yaml = yaml.load(open(f, 'r'), Loader=yaml.FullLoader)
    out.append(str(calendar_from_yaml(calendar_yaml)))

print('\n'.join(out))
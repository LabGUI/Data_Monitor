# This sends the emails

from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import logger

logging = logger.Logger(__file__)
from localvars import *
from tabulate import tabulate

def _write_alert_email(triggered_monitors_str, data_dump_str):
    return f"""
The following monitors triggered this alert:
{triggered_monitors_str}

Fridge log dump:
{data_dump_str}

Sincerely,
BlueFors Fridge
"""

def _write_test_email(data_dump_str):
    return f"""
Do not panic, this test email was manually triggered to test the Bluefors Monitor System

Fridge log dump:
{data_dump_str}

Sincerely,
BlueFors Fridge
"""

def _send_email(subject, body, sender, recipients, password, smtp = 'smtp.gmail.com', smtp_port = 465):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL(smtp, smtp_port) as smtp_server:
       smtp_server.login(sender, password)
       smtp_server.sendmail(sender, recipients, msg.as_string())
    return True


class Mailer:
    def __init__(self, recipients, email=SENDER, password=PASSWORD):
        self.recipients = recipients
        self.email = email
        self.password = password


    def stringTriggeredMonitors(self, monitors, all_values):
        triggered_monitors_str = "\n".join([
            f"{channel} is {obj['monitor']}\n\t" + "\n\t".join([
                f"Read '{v}' at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}"  # single channel
                for t, v in obj['currentValue']
            ])
            if 'currentValue' in obj else  # type(obj['currentValue']) == list else  # if single channel else has subchannels
            "\n".join([
                f"{channel}:{subchannel} is {vobj['monitor']}\n\t" + "\n\t".join([
                    f"Read '{v}' at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}"
                    # single channel
                    for t, v in vobj['currentValue'].items()
                ])
                # ({vobj['currentValue'][1]} at {datetime.fromtimestamp(vobj['currentValue'][0]).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}))"
                for subchannel, vobj in obj.items()
            ])
            for channel, obj in monitors.items()
        ])
        return triggered_monitors_str

    def stringTabulatedDataDump(self, all_values):
        tabulated_data_dump_str = str(tabulate(
            sum([
                [
                    (f"{channel}:{subchannel}", val, datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}'))
                    for subchannel, val in v.items()
                ]
                if type(v) == dict else
                [(channel, v, datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}'))]
                for channel, (t, v) in all_values.items()
            ],[]),
            headers=['Channel', 'Value', 'Last Read Time'],
            tablefmt=TABULATE_TABLE_FMT,
        ))
        return tabulated_data_dump_str

    def send_alert(self, monitors, all_values):
        subject = '[URGENT] BlueFors Alert Triggered!'

        triggered_monitors_str = self.stringTriggeredMonitors(monitors, all_values)
        data_dump_str = self.stringTabulatedDataDump(all_values)
        if INDENT_EMAIL_INFORMATION:
            triggered_monitors_str = "\t" + "\n\t".join(triggered_monitors_str.split('\n'))
            data_dump_str = "\t" + "\n\t".join(data_dump_str.split('\n'))
        text = _write_alert_email(triggered_monitors_str, data_dump_str)
        if DEBUG_MODE:
            current_time = datetime.now().strftime(f"{DATE_FORMAT}_{TIME_FORMAT}")
            with open(f"./testEmails/alert_{current_time.replace(':','-')}.email", 'w', encoding='utf-8') as f:
                f.write(f"Subject: {subject}\n")
                f.write(f"Recipients: {', '.join(RECIPIENTS)}\n")
                f.write(f"Body:\n")
                f.write(text)
        else:
            self._send_email(subject, text)


    def send_test(self, all_values):
        subject = '[TEST] BlueFors Alert Test Email'

        data_dump_str = self.stringTabulatedDataDump(all_values)
        text = _write_test_email(data_dump_str)
        if DEBUG_MODE:
            current_time = datetime.now().strftime(f"{DATE_FORMAT}_{TIME_FORMAT}")
            with open(f"{ROOT_DIR}/testEmails/alert_{current_time.replace(':','-')}.email", 'w', encoding='utf-8') as f:
                f.write(f"Subject: {subject}\n")
                f.write(f"Recipients: {', '.join(RECIPIENTS)}\n")
                f.write(f"Body:\n")
                f.write(text)
        else:
            self._send_email(subject, text)



    def _send_email(self, subject, text):
        # THis sends the email with smptlib
        try:
            _send_email(
                subject=subject,
                body=text,
                sender=self.email,
                recipients=self.recipients,
                password=self.password
            )
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")

    def _possible_str_alerts(self, monitors, all_values):
        triggered_monitors_str = "\n".join([
            f"{channel} is {obj['monitor']}\n\t" + "\n\t".join([
                f"Read '{v}' at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')})"  # single channel
                for t, v in obj['currentValue']
            ])
            if 'currentValue' in obj else  # type(obj['currentValue']) == list else  # if single channel else has subchannels
            "\n".join([
                f"{channel}:{subchannel} is {vobj['monitor']}\n\t" + "\n\t".join([
                    f"Read '{v}' at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')})"
                    # single channel
                    for t, v in vobj['currentValue'].items()
                ])
                # ({vobj['currentValue'][1]} at {datetime.fromtimestamp(vobj['currentValue'][0]).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}))"
                for subchannel, vobj in obj.items()
            ])
            for channel, obj in monitors.items()
        ])

        ordered_data_dump_str = "\n".join([
            "\n".join([
                f"{channel}:{subchannel} = {val} at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}"
                for subchannel, val in v.items()
            ])
            if type(v) == dict else
            f"{channel} = {v} at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}"
            for channel, (t, v) in all_values.items()
        ])
        chronological_data_dump_str = "\n".join([
            "\n".join([
                f"{datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')} - {channel}:{subchannel} = {val}"
                for subchannel, val in v.items()
            ])
            if type(v) == dict else
            f"{datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')} - {channel} = {v}"
            for channel, (t, v) in reversed(sorted(all_values.items(), key=lambda x: x[1][0]))
        ])
        data_dump_str = "\n".join([
            f"{channel} is {obj['monitor']}\n\t" + "\n\t".join([
                f"Read '{v}' at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')})"  # single channel
                for t, v in obj['currentValue']
            ])
            if 'currentValue' in obj else  # type(obj['currentValue']) == list else  # if single channel else has subchannels
            "\n".join([
                f"{channel}:{subchannel} is {vobj['monitor']}\n\t" + "\n\t".join([
                    f"Read '{v}' at {datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')})"
                    # single channel
                    for t, v in vobj['currentValue'].items()
                ])
                # ({vobj['currentValue'][1]} at {datetime.fromtimestamp(vobj['currentValue'][0]).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')}))"
                for subchannel, vobj in obj.items()
            ])
            for channel, obj in monitors.items()
        ])
        tabulated_data_dump_str = str(tabulate(
            [
                sum([
                    [f"{channel}:{subchannel}", val, datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')]
                    for subchannel, val in v.items()
                ], [])
                if type(v) == dict else
                [channel, v, datetime.fromtimestamp(t).strftime(f'{DATE_FORMAT} {TIME_FORMAT}')]
                for channel, (t, v) in all_values.items()
            ],
            headers=['Channel', 'Value', 'Read Time'],
            tablefmt=TABULATE_TABLE_FMT,
        ))
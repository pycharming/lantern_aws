from email.mime.text import MIMEText
import smtplib


instance_id = "{{ grains['id'] }}"

# {% from 'ip.sls' import external_ip %}
ip = "{{ external_ip(grains) }}"


def send_mail(from_, to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_, [to], msg.as_string())
    s.close()

def send_alarm(subject, body):
    send_mail('lantern@%s' % instance_id,
              'fallback-alarms@getlantern.org',
              subject,
              "%s (%s) reports: %s" % (instance_id,
                                       ip,
                                       body))

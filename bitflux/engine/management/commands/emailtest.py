import smtplib

EMAIL_LIST = {'kyle@schinkels.net','stephanie@schinkels.net'}
EMAIL_FROM_ADDR = 'bitflux@schinkels.net'
EMAIL_FROM_PASSWD = '~bitflux~'

fromaddr = EMAIL_FROM_ADDR
toaddrs  = 'kyle@schinkels.net'
msg = ("From: %s\r\nTo: %s\r\n\r\n"
       % (fromaddr, toaddrs))

msg = msg + 'TESTING'

print "Message length is " + repr(len(msg))

server = smtplib.SMTP('smtp.gmail.com', 587)
server.ehlo()
server.starttls()
server.ehlo()
server.login(EMAIL_FROM_ADDR, EMAIL_FROM_PASSWD)
server.set_debuglevel(1)
server.sendmail(fromaddr, toaddrs, msg)
server.quit()

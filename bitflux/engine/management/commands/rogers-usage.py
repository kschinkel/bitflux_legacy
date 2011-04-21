import urllib, urllib2, cookielib

username = 'G1TRD0N3'
password = 'y101country'

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

login_data = urllib.urlencode({'SMAUTHREASON' : 0, 'TARGET' : 'https://www.rogers.com/web/loginSuccess.jsp','USER':username,'password':password,'signinPassword1Hp':'Enter Password'})
'''SMAUTHREASON=0
TARGET=https://www.rogers.com/web/loginSuccess.jsp
USER=<username>
password=<password>
signinPassword1Hp=Enter Password
  to https://www.rogers.com/siteminderagent/forms/login.fcc'''
  
opener.open('https://www.rogers.com/siteminderagent/forms/login.fcc', login_data)
#resp = opener.open('https://www.rogers.com/web/RogersServices.portal?_nfpb=true&_pageLabel=Overview')
resp = opener.open('https://www.rogers.com/web/myrogers/internetUsageBeta')
output = resp.read()
resp.close()
my_string = "Usage to date:"
usage_index = output.find(my_string)+len(my_string)
label = "<label>"
label_index = output.find(label,usage_index)+len(label)

print "ISP Reported Usage:", output[label_index:output.find('</label>',label_index)] + "GB"
#f = open('rogers_output.html','w')
#f.write(resp.read())


#https://www.rogers.com/web/Rogers.portal
#https://www.rogers.com/web/RogersServices.portal?_nfpb=true&_pageLabel=Overview
import requests
import time

def check_availability():
    url = "https://ielts.idp.com/api/testsession/availability"
    params = {
        "countryId": 212,
        "testCentreId": 11995,
        "testVenueId": 1771,
        "testCentreLocationId": 1654,
        "testSessionDate": "2025-06-28T00:00:00.0000000",
        "isSelt": "false",
        "restrictToSpecifiedDate": "true",
        "testmoduleid": 1,
        "token": "d02942a0c5bfd2446de2c0049cc303a0137f98b43ee5d5266201ebfdc4778cad" #bu tokenın validasyonu sıkıntılı olabilir
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        # BIACH burada data analizi yapılacak dostum
        informUsers()
        print(data)
    else:
        print(f"Error: {response.status_code}")
    
def informUsers():
    #SQL den bütün kullanıcıların numaraları alınacak ya da bir mesaj - bildirim gönderilecek

while True:
    check_availability()
    time.sleep(600)  # 600 sn de 1 bakıleür  

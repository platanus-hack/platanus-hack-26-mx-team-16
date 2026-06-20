from src.common.domain.enums.base_enum import BaseEnum


class TimeZone(BaseEnum):
    # Check pytz.all_timezones if you need to add more timezones
    UTC = "UTC"
    MEXICO_CITY = "America/Mexico_City"
    MEXICO_BAJA_NORTE = "Mexico/BajaNorte"
    MEXICO_BAJA_SUR = "Mexico/BajaSur"
    MEXICO_GENERAL = "Mexico/General"
    AMERICA_LA_PAZ = "America/La_Paz"

    ASIA_KABUL = "Asia/Kabul"
    EUROPE_MARIEHAMN = "Europe/Mariehamn"
    EUROPE_TIRANE = "Europe/Tirane"
    AFRICA_ALGIERS = "Africa/Algiers"
    PACIFIC_PAGO_PAGO = "Pacific/Pago_Pago"
    AFRICA_LUANDA = "Africa/Luanda"
    AMERICA_ANGUILLA = "America/Anguilla"
    ANTARCTICA_MCMURDO = "Antarctica/McMurdo"
    AMERICA_ANTIGUA = "America/Antigua"
    AMERICA_ARGENTINA_BUENOS_AIRES = "America/Argentina/Buenos_Aires"
    ASIA_YEREVAN = "Asia/Yerevan"
    AMERICA_ARUBA = "America/Aruba"
    AUSTRALIA_SYDNEY = "Australia/Sydney"
    EUROPE_VIENNA = "Europe/Vienna"
    ASIA_BAKU = "Asia/Baku"
    AMERICA_NASSAU = "America/Nassau"
    ASIA_BAHRAIN = "Asia/Bahrain"
    ASIA_DHAKA = "Asia/Dhaka"
    AMERICA_BARBADOS = "America/Barbados"
    EUROPE_MINSK = "Europe/Minsk"
    EUROPE_BRUSSELS = "Europe/Brussels"
    AMERICA_BELIZE = "America/Belize"
    AFRICA_PORTO_NOVO = "Africa/Porto-Novo"
    ATLANTIC_BERMUDA = "Atlantic/Bermuda"
    ASIA_THIMPHU = "Asia/Thimphu"
    EUROPE_SARAJEVO = "Europe/Sarajevo"
    AFRICA_GABORONE = "Africa/Gaborone"
    ANTARCTICA_TROLL = "Antarctica/Troll"
    AMERICA_SAO_PAULO = "America/Sao_Paulo"
    INDIAN_CHAGOS = "Indian/Chagos"
    ASIA_BRUNEI = "Asia/Brunei"
    EUROPE_SOFIA = "Europe/Sofia"
    AFRICA_OUAGADOUGOU = "Africa/Ouagadougou"
    AFRICA_BUJUMBURA = "Africa/Bujumbura"
    ASIA_PHNOM_PENH = "Asia/Phnom_Penh"
    AFRICA_DOUALA = "Africa/Douala"
    AMERICA_TORONTO = "America/Toronto"
    ATLANTIC_CAPE_VERDE = "Atlantic/Cape_Verde"
    AMERICA_CAYMAN = "America/Cayman"
    AFRICA_BANGUI = "Africa/Bangui"
    AFRICA_NDJAMENA = "Africa/Ndjamena"
    AMERICA_SANTIAGO = "America/Santiago"
    ASIA_SHANGHAI = "Asia/Shanghai"
    ASIA_PERTH = "Asia/Perth"
    AMERICA_BOGOTA = "America/Bogota"
    INDIAN_COMORO = "Indian/Comoro"
    AFRICA_BRAZZAVILLE = "Africa/Brazzaville"
    AFRICA_KINSHASA = "Africa/Kinshasa"
    PACIFIC_RAROTONGA = "Pacific/Rarotonga"
    AMERICA_COSTA_RICA = "America/Costa_Rica"
    EUROPE_ZAGREB = "Europe/Zagreb"
    AMERICA_HAVANA = "America/Havana"
    ASIA_NICOSIA = "Asia/Nicosia"
    EUROPE_PRAGUE = "Europe/Prague"
    EUROPE_COPENHAGEN = "Europe/Copenhagen"
    AFRICA_DJIBOUTI = "Africa/Djibouti"
    AMERICA_DOMINICA = "America/Dominica"
    AMERICA_SANTO_DOMINGO = "America/Santo_Domingo"
    AMERICA_GUAYAQUIL = "America/Guayaquil"
    AFRICA_CAIRO = "Africa/Cairo"
    AMERICA_EL_SALVADOR = "America/El_Salvador"
    AFRICA_MALABO = "Africa/Malabo"
    AFRICA_ASMARA = "Africa/Asmara"
    EUROPE_TALLINN = "Europe/Tallinn"
    AFRICA_ADDIS_ABABA = "Africa/Addis_Ababa"
    ATLANTIC_STANLEY = "Atlantic/Stanley"
    ATLANTIC_FAROE = "Atlantic/Faroe"
    PACIFIC_FIJI = "Pacific/Fiji"
    EUROPE_HELSINKI = "Europe/Helsinki"
    EUROPE_PARIS = "Europe/Paris"
    AMERICA_CAYENNE = "America/Cayenne"
    PACIFIC_TAHITI = "Pacific/Tahiti"
    INDIAN_KERGUELEN = "Indian/Kerguelen"
    AFRICA_LIBREVILLE = "Africa/Libreville"
    AFRICA_BANJUL = "Africa/Banjul"
    ASIA_TBILISI = "Asia/Tbilisi"
    EUROPE_BERLIN = "Europe/Berlin"
    AFRICA_ACCRA = "Africa/Accra"
    EUROPE_GIBRALTAR = "Europe/Gibraltar"
    EUROPE_ATHENS = "Europe/Athens"
    AMERICA_GODTHAB = "America/Godthab"
    AMERICA_GRENADA = "America/Grenada"
    AMERICA_GUADELOUPE = "America/Guadeloupe"
    PACIFIC_GUAM = "Pacific/Guam"
    AMERICA_GUATEMALA = "America/Guatemala"
    EUROPE_GUERNSEY = "Europe/Guernsey"
    AFRICA_CONAKRY = "Africa/Conakry"
    AFRICA_BISSAU = "Africa/Bissau"
    AMERICA_GUYANA = "America/Guyana"
    AMERICA_PORT_AU_PRINCE = "America/Port-au-Prince"
    EUROPE_VATICAN = "Europe/Vatican"
    AMERICA_TEGUCIGALPA = "America/Tegucigalpa"
    ASIA_HONG_KONG = "Asia/Hong_Kong"
    EUROPE_BUDAPEST = "Europe/Budapest"
    ATLANTIC_REYKJAVIK = "Atlantic/Reykjavik"
    ASIA_KOLKATA = "Asia/Kolkata"
    ASIA_JAKARTA = "Asia/Jakarta"
    ASIA_TEHRAN = "Asia/Tehran"
    ASIA_BAGHDAD = "Asia/Baghdad"
    EUROPE_DUBLIN = "Europe/Dublin"
    ASIA_JERUSALEM = "Asia/Jerusalem"
    EUROPE_ROME = "Europe/Rome"
    AMERICA_JAMAICA = "America/Jamaica"
    ASIA_TOKYO = "Asia/Tokyo"
    EUROPE_LONDON = "Europe/London"
    ASIA_AMMAN = "Asia/Amman"
    ASIA_ALMATY = "Asia/Almaty"
    AFRICA_NAIROBI = "Africa/Nairobi"
    PACIFIC_TARAWA = "Pacific/Tarawa"
    ASIA_PYONGYANG = "Asia/Pyongyang"
    ASIA_SEOUL = "Asia/Seoul"
    ASIA_KUWAIT = "Asia/Kuwait"
    ASIA_BISHKEK = "Asia/Bishkek"
    ASIA_VIENTIANE = "Asia/Vientiane"
    EUROPE_RIGA = "Europe/Riga"
    ASIA_BEIRUT = "Asia/Beirut"
    AFRICA_MASERU = "Africa/Maseru"
    AFRICA_MONROVIA = "Africa/Monrovia"
    AFRICA_TRIPOLI = "Africa/Tripoli"
    EUROPE_VADUZ = "Europe/Vaduz"
    EUROPE_VILNIUS = "Europe/Vilnius"
    EUROPE_LUXEMBOURG = "Europe/Luxembourg"
    ASIA_MACAU = "Asia/Macau"
    EUROPE_SKOPJE = "Europe/Skopje"
    INDIAN_ANTANANARIVO = "Indian/Antananarivo"
    AFRICA_BLANTYRE = "Africa/Blantyre"
    ASIA_KUALA_LUMPUR = "Asia/Kuala_Lumpur"
    INDIAN_MALDIVES = "Indian/Maldives"
    AFRICA_BAMAKO = "Africa/Bamako"
    EUROPE_MALTA = "Europe/Malta"
    PACIFIC_MAJURO = "Pacific/Majuro"
    AMERICA_MARTINIQUE = "America/Martinique"
    AFRICA_NOUAKCHOTT = "Africa/Nouakchott"
    INDIAN_MAURITIUS = "Indian/Mauritius"
    INDIAN_MAYOTTE = "Indian/Mayotte"
    AMERICA_MEXICO_CITY = "America/Mexico_City"
    PACIFIC_CHUUK = "Pacific/Chuuk"
    EUROPE_CHISINAU = "Europe/Chisinau"
    EUROPE_MONACO = "Europe/Monaco"
    ASIA_ULAN_BATOR = "Asia/Ulaanbaatar"
    EUROPE_PODGORICA = "Europe/Podgorica"
    AMERICA_MONTSERRAT = "America/Montserrat"
    AFRICA_CASABLANCA = "Africa/Casablanca"
    AFRICA_MAPUTO = "Africa/Maputo"
    ASIA_YANGON = "Asia/Yangon"
    AFRICA_WINDHOEK = "Africa/Windhoek"
    PACIFIC_NAURU = "Pacific/Nauru"
    ASIA_KATHMANDU = "Asia/Kathmandu"
    EUROPE_AMSTERDAM = "Europe/Amsterdam"
    AMERICA_CURACAO = "America/Curacao"
    PACIFIC_NOUMEA = "Pacific/Noumea"
    PACIFIC_AUCKLAND = "Pacific/Auckland"
    AMERICA_MANAGUA = "America/Managua"
    AFRICA_NIAMEY = "Africa/Niamey"
    AFRICA_LAGOS = "Africa/Lagos"
    PACIFIC_NIUE = "Pacific/Niue"
    PACIFIC_NORFOLK = "Pacific/Norfolk"
    PACIFIC_SAIPAN = "Pacific/Saipan"
    EUROPE_OSLO = "Europe/Oslo"
    ASIA_MUSCAT = "Asia/Muscat"
    ASIA_KARACHI = "Asia/Karachi"
    PACIFIC_PALAU = "Pacific/Palau"
    ASIA_GAZA = "Asia/Gaza"
    AMERICA_PANAMA = "America/Panama"
    PACIFIC_PORT_MORESBY = "Pacific/Port_Moresby"
    AMERICA_ASUNCION = "America/Asuncion"
    AMERICA_LIMA = "America/Lima"
    ASIA_MANILA = "Asia/Manila"
    PACIFIC_PITCAIRN = "Pacific/Pitcairn"
    EUROPE_WARSAW = "Europe/Warsaw"
    EUROPE_LISBON = "Europe/Lisbon"
    AMERICA_PUERTO_RICO = "America/Puerto_Rico"
    ASIA_QATAR = "Asia/Qatar"
    INDIAN_REUNION = "Indian/Reunion"
    EUROPE_BUCHAREST = "Europe/Bucharest"
    EUROPE_MOSCOW = "Europe/Moscow"
    AFRICA_KIGALI = "Africa/Kigali"
    AFRICA_ASCENSION = "Africa/Ascension"
    AMERICA_ST_KITTS = "America/St_Kitts"
    AMERICA_ST_LUCIA = "America/St_Lucia"
    AMERICA_MIQUELON = "America/Miquelon"
    AMERICA_ST_VINCENT = "America/St_Vincent"
    PACIFIC_APIA = "Pacific/Apia"
    EUROPE_SAN_MARINO = "Europe/San_Marino"
    AFRICA_SAO_TOME = "Africa/Sao_Tome"
    ASIA_RIYADH = "Asia/Riyadh"
    AFRICA_DAKAR = "Africa/Dakar"
    EUROPE_BELGRADE = "Europe/Belgrade"
    INDIAN_MAHE = "Indian/Mahe"
    AFRICA_FREETOWN = "Africa/Freetown"
    ASIA_SINGAPORE = "Asia/Singapore"
    EUROPE_BRATISLAVA = "Europe/Bratislava"
    EUROPE_LJUBLJANA = "Europe/Ljubljana"
    PACIFIC_GUADALCANAL = "Pacific/Guadalcanal"
    AFRICA_MOGADISHU = "Africa/Mogadishu"
    AFRICA_JOHANNESBURG = "Africa/Johannesburg"
    ATLANTIC_SOUTH_GEORGIA = "Atlantic/South_Georgia"
    EUROPE_MADRID = "Europe/Madrid"
    ASIA_COLOMBO = "Asia/Colombo"
    AFRICA_KHARTOUM = "Africa/Khartoum"
    AMERICA_PARAMARIBO = "America/Paramaribo"
    ARCTIC_LONGYEARBYEN = "Arctic/Longyearbyen"
    AFRICA_MBABANE = "Africa/Mbabane"
    EUROPE_STOCKHOLM = "Europe/Stockholm"
    EUROPE_ZURICH = "Europe/Zurich"
    ASIA_DAMASCUS = "Asia/Damascus"
    ASIA_TAIPEI = "Asia/Taipei"
    ASIA_DUSHANBE = "Asia/Dushanbe"
    AFRICA_DAR_ES_SALAAM = "Africa/Dar_es_Salaam"
    ASIA_BANGKOK = "Asia/Bangkok"
    ASIA_DILI = "Asia/Dili"
    AFRICA_LOME = "Africa/Lome"
    PACIFIC_FAKAOFO = "Pacific/Fakaofo"
    PACIFIC_TONGATAPU = "Pacific/Tongatapu"
    AMERICA_PORT_OF_SPAIN = "America/Port_of_Spain"
    AFRICA_TUNIS = "Africa/Tunis"
    EUROPE_ISTANBUL = "Europe/Istanbul"
    ASIA_ASHGABAT = "Asia/Ashgabat"
    AMERICA_GRAND_TURK = "America/Grand_Turk"
    PACIFIC_FUNAFUTI = "Pacific/Funafuti"
    AFRICA_KAMPALA = "Africa/Kampala"
    EUROPE_KIEV = "Europe/Kiev"
    ASIA_DUBAI = "Asia/Dubai"
    AMERICA_NEW_YORK = "America/New_York"
    AMERICA_MONTEVIDEO = "America/Montevideo"
    ASIA_TASHKENT = "Asia/Tashkent"
    PACIFIC_EFATE = "Pacific/Efate"
    AMERICA_CARACAS = "America/Caracas"
    ASIA_HO_CHI_MINH = "Asia/Ho_Chi_Minh"
    AMERICA_TORTOLA = "America/Tortola"
    AMERICA_ST_THOMAS = "America/St_Thomas"
    PACIFIC_WALLIS = "Pacific/Wallis"
    AFRICA_EL_AAIUN = "Africa/El_Aaiun"
    ASIA_ADEN = "Asia/Aden"
    AFRICA_LUSAKA = "Africa/Lusaka"
    AFRICA_HARARE = "Africa/Harare"


class Days(BaseEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    @classmethod
    def weekdays(cls):
        return {
            cls.MONDAY: "MONDAY",
            cls.TUESDAY: "TUESDAY",
            cls.WEDNESDAY: "WEDNESDAY",
            cls.THURSDAY: "THURSDAY",
            cls.FRIDAY: "FRIDAY",
            cls.SATURDAY: "SATURDAY",
            cls.SUNDAY: "SUNDAY",
        }

    @classmethod
    def week(cls):
        return [
            cls.MONDAY,
            cls.TUESDAY,
            cls.WEDNESDAY,
            cls.THURSDAY,
            cls.FRIDAY,
            cls.SATURDAY,
            cls.SUNDAY,
        ]

    @classmethod
    def choices(cls):
        return [(weekday.value, day_str) for weekday, day_str in cls.weekdays().items()]

    @classmethod
    def get_weekday_label(cls, day: "Days"):
        return cls.weekdays().get(day, None)


class Language(BaseEnum):
    ES = "es"
    EN = "en"


class Platform(BaseEnum):
    ANDROID = "ANDROID"
    IOS = "IOS"

    @classmethod
    def choices(cls):
        return (
            (cls.ANDROID.value, "ANDROID"),
            (cls.IOS.value, "IOS"),
        )

# backend/kerala_local_bodies.py
# ============================================================
# Complete Kerala Local Bodies — Official Data from LGD
# Grama Panchayats: 941 | Municipalities: 87 | Corporations: 6
# Source: lgdirectory.gov.in — Kerala State Election Commission
# ============================================================

KERALA_LOCAL_BODIES = {
    "Alappuzha": {
        "grama_panchayat": [
            "Ala", "Ambalappuzha ( North )", "Ambalappuzha(South)", "Arattupuzha", "Arookutty",
            "Aroor", "Aryad", "Bharanikkavu", "Budhannoor", "Champakkulam",
            "Chennampalippuram", "Chennithala Thriperumthara", "Cheppad", "Cheriyanad", "Cherthala South",
            "Cheruthana", "Chettikulangara", "Chingoli", "Chunakkara", "Devikulangara",
            "Edathua", "Ezhupunna", "Kadakkarappally", "Kainakary", "Kandalloor",
            "Kanjikuzhi", "Karthikappally", "Karuvatta", "Kavalam", "Kodamthuruthu",
            "Krishnapuram", "Kumarapuram", "Kuthiathodu", "Mannanchery", "Mannar",
            "Mararikkulam North", "Mararikkulam South", "Mavelikkara Thamarakkulam", "Mavelikkara Thekkekara", "Muhamma",
            "Mulakkuzha", "Muthukulam", "Muttar", "Nedumudi", "Neelamperoor",
            "Nooranad", "Palamel", "Pallippad", "Panavally", "Pandanad",
            "Pathiyoor", "Pattanakkad", "Perumbalam", "Pulinkunnu", "Puliyoor",
            "Punnapra (North)", "Punnapra(South)", "Purakkad", "Ramankari", "Thaicattussery",
            "Thakazhi", "Thalavadi", "Thanneermukkam", "Thazhakkara", "Thiruvanvandur",
            "Thrikkunnapuzha", "Thuravoor", "Vallikunnam", "Vayalar", "Veeyapuram",
            "Veliyanad", "Venmony"
        ],
        "municipality": ['Alappuzha', 'Chengannur', 'Cherthala', 'Harippad', 'Kayamkulam', 'Mavelikkara'],
        "corporation": [],
    },
    "Ernakulam": {
        "grama_panchayat": [
            "Aikkaranad", "Alangad", "Amballur", "Arakuzha", "Asamannoor",
            "Avoly", "Ayavana", "Ayyampuzha", "Chellanam", "Chendamangalam",
            "Chengamanad", "Cheranallur", "Chittattukara", "Choornikkara", "Chottanikkara",
            "Edakkattuvayal", "Edathala", "Edavanakkad", "Elamkunnapuzha", "Elanji",
            "Ezhikkara", "Kadamakkudy", "Kadungallur", "Kalady", "Kalloorkkad",
            "Kanjoor", "Karukutty", "Karumalloor", "Kavalangad", "Keerampara",
            "Keezhmad", "Kizhakkambalam", "Koovappady", "Kottappady", "Kottuvally",
            "Kumbalam", "Kumbalangy", "Kunnathunad", "Kunnukara", "Kuttampuzha",
            "Kuzhuppilly", "Malayattoor Neeleswaram", "Maneed", "Manjalloor", "Manjapra",
            "Marady", "Mazhuvannoor", "Mookkannur", "Mudakuzha", "Mulavukad",
            "Mulumthuruthy", "Nayarambalam", "Nedumbassery", "Nellikkuzhi", "Njarakkal",
            "Okkal", "Paingottur", "Paipra", "Palakuzha", "Pallarimangalam",
            "Pallippuram", "Pampakuda", "Parakkadavu", "Pindimana", "Poothrikka",
            "Pothanikkad", "Puthenvelikkara", "Ramamangalam", "Rayamangalam", "Sreemoolanagaram",
            "Thirumarady", "Thiruvaniyoor", "Thuravoor", "Udayamperur", "Vadakkekara",
            "Vadavucode Puthen Cruz", "Valakom", "Varappetty", "Varapuzha", "Vazhakkulam",
            "Vengola", "Vengoor"
        ],
        "municipality": ['Aluva', 'Angamaly', 'Eloor', 'Kalamassery', 'Koothattukulam', 'Kothamangalam', 'Maradu', 'Muvattupuzha', 'Paravoor', 'Perumbavoor', 'Thrikkakara', 'Thrippunithura'],
        "corporation": ['Kochi'],
    },
    "Idukki": {
        "grama_panchayat": [
            "Adimaly", "Alakkode", "Arakulam", "Ayyappancoil", "Bisonvalley",
            "Chakkupallam", "Chinnakanal", "Devikulam", "Edamalakkudy", "Edavetty",
            "Elappara", "Erattayar", "Idukki - Kanjikuzhy", "Kamakshy", "Kanchiyar",
            "Kanthalloor", "Karimannoor", "Karimkunnam", "Karunapuram", "Kodikulam",
            "Kokkayar", "Konnathady", "Kudayathoor", "Kumaly", "Kumaramangalam",
            "Manakkad", "Mankulam", "Marayoor", "Mariyapuram", "Munnar",
            "Muttom", "Nedumkandam", "Pallivasal", "Pampadumpara", "Peerumedu",
            "Peruvanthanam", "Purapuzha", "Rajakkad", "Rajakumari", "Santhanpara",
            "Senapathy", "Udumbanchola", "Udumbanoor", "Upputhara", "Vandenmedu",
            "Vandiperiyar", "Vannapuram", "Vathikudy", "Vattavada", "Vazhathope",
            "Vellathooval", "Velliyamattom"
        ],
        "municipality": ['Kattappana', 'Thodupuzha'],
        "corporation": [],
    },
    "Kannur": {
        "grama_panchayat": [
            "Alakode", "Ancharakandy", "Aralam", "Ayyankunnu", "Azhikode",
            "Chapparapadavu", "Chembilode", "Chengalai", "Cherukunnu", "Cherupuzha",
            "Cheruthazham", "Chirakkal", "Chittariparamba", "Chokli", "Dharmadam",
            "Eramam -Kuttoor", "Eranholi", "Eruvessey", "Ezhome", "Irikkur",
            "Kadamboor", "Kadannapally -Panapuzha", "Kadirur", "Kalliassery", "Kanichar",
            "Kankole- Alapadamba", "Kannapuram", "Karivellur -Peralam", "Keezhallur", "Kelakam",
            "Kolacherry", "Kolayad", "Koodali", "Kottayam", "Kottiyoor",
            "Kunhimangalam", "Kunnathuparamba", "Kurumathur", "Kuttiattor", "Madayi",
            "Malapattom", "Malur", "Mangattidom", "Mattool", "Mayyil",
            "Mokeri", "Munderi", "Muzhakkunnu", "Muzhappilangad", "Naduvil",
            "Narath", "New Mahi", "Padiyur", "Panniyannur", "Pappinisseri",
            "Pariyaram", "Pattiam", "Pattuvam", "Payam", "Payyavoor",
            "Peralasseri", "Peravoor", "Peringome -Vayakkara", "Pinarayi", "Ramanthali",
            "Thillankeri", "Trippangottur", "Udayagiri", "Ulikkal", "Valapattanam",
            "Vengad"
        ],
        "municipality": ['Anthur', 'Iritty', 'Koothuparamba', 'Mattannur', 'Panoor', 'Payyannur', 'Sreekandapuram', 'Taliparamba', 'Thalassery'],
        "corporation": ['Kannur'],
    },
    "Kasaragod": {
        "grama_panchayat": [
            "Ajanoor", "Badiyadka", "Balal", "Bedaduka", "Belloor",
            "Chemnad", "Chengala", "Cheruvathur", "Delampady", "East Eleri",
            "Enmakaje", "Kallar", "Karadka", "Kayyur Cheemeni", "Kinanoor Karindalam",
            "Kodombellur", "Kumbadaje", "Kumbala", "Kutikkol", "Madhur",
            "Madikkai", "Mangalpady", "Manjewswaram", "Meenja", "Mogral Puthur",
            "Muliyar", "Padne", "Paivalike", "Pallikkara", "Panathady",
            "Pilicode", "Pullurperiya", "Puthige", "Thrikkaripur", "Udma",
            "Valiyaparamba", "Vorkady", "West Eleri"
        ],
        "municipality": ['Kanhangad', 'Kasaragod', 'Nileshwar'],
        "corporation": [],
    },
    "Kollam": {
        "grama_panchayat": [
            "Adichanalloor", "Alappad", "Alayamon", "Anchal", "Ariencavu",
            "Chadayamangalam", "Chathannur", "Chavara", "Chirakkara", "Chithara",
            "Clappana", "Edamulakkal", "Elamadu", "Elamballur", "Eroor",
            "Ezhukone", "Ittiva", "Kadakkal", "Kalluvathukkal", "Karavaloor",
            "Kareepra", "Kizhakkekallada", "Kottamkara", "Kulakkada", "Kulasekharapuram",
            "Kulathupuzha", "Kummil", "Kundara", "Kunnathur", "Mayyanad",
            "Melila", "Mundrothuruthu", "Mylam", "Mynagappally", "Nedumpana",
            "Neduvathur", "Neendakara", "Nilamel", "Oachira", "Panayam",
            "Panmana", "Pathanapuram", "Pattazhi", "Pattazhi Vadakkekara", "Pavithreswaram",
            "Perayam", "Perinad", "Piravanthur", "Poothakkulam", "Pooyappally",
            "Poruvazhy", "Sasthancotta", "Sooranad North", "Sooranad South", "Thalavoor",
            "Thazhava", "Thekkumbhagam", "Thenmala", "Thevalakkara", "Thodiyoor",
            "Thrikkaruva", "Thrikkovilvattom", "Ummannur", "Velinallur", "Veliyam",
            "Vettikkavala", "Vilakudy", "West Kallada"
        ],
        "municipality": ['Karunagappally', 'Kottarakkara', 'Paravur', 'Punalur'],
        "corporation": ['Kollam'],
    },
    "Kottayam": {
        "grama_panchayat": [
            "Akalakunnam", "Arpookara", "Athirampuzha", "Ayarkkunnam", "Aymanam",
            "Bharananganam", "Chempu", "Chirakkadavu", "Elikulam", "Erumeli",
            "Kadanad", "Kadaplamattom", "Kaduthuruthy", "Kallara", "Kanakkari",
            "Kangazha", "Kanjirappally", "Karoor", "Karukachal", "Kidangoor",
            "Kooroppada", "Koottickal", "Koruthode", "Kozhuvanal", "Kumarakom",
            "Kuravilangad", "Kurichy", "Madappally", "Manimala", "Manjoor",
            "Mannarkadu", "Marangattupilly", "Maravanthuruthu", "Meenachil", "Meenadom",
            "Melukavu", "Moonilavu", "Mulakulam", "Mundakayam", "Mutholy",
            "Nedumkunnam", "Neendoor", "Njeezhoor", "Paippad", "Pallikkathode",
            "Pampady", "Panachikkad", "Parathode", "Poonjar", "Poonjar Thekkekara",
            "Puthuppally", "Ramapuram", "Teekoy", "Thalanad", "Thalappalam",
            "Thalayazham", "Thalayolaparambu", "Thidanad", "Thiruvarpu", "Thrikkodithanam",
            "Tv Puram", "Udayanapuram", "Uzhavoor", "Vakathanam", "Vazhappally",
            "Vazhoor", "Vechoor", "Veliyannoor", "Vellavoor", "Velloor",
            "Vijayapuram"
        ],
        "municipality": ['Changanassery', 'Erattupetta', 'Ettumanoor', 'Kottayam', 'Palai', 'Piravom', 'Vaikom'],
        "corporation": [],
    },
    "Kozhikode": {
        "grama_panchayat": [
            "Arikulam", "Atholi", "Ayancheri", "Azhiyur", "Balusseri",
            "Chakittapara", "Changaroth", "Chathamangalam", "Chekkiad", "Chelannur",
            "Chemanachery", "Chengottukavu", "Cheruvannur", "Chorode", "Edacheri",
            "Eramala", "Kadalundi", "Kakkodi", "Kakkur", "Karasseri",
            "Kattippara", "Kavilumpara", "Kayakkodi", "Kayanna", "Keezhariyur",
            "Kizhakkoth", "Kodencheri", "Kodiyathur", "Koodaranji", "Koorachundu",
            "Koothali", "Kottur", "Kunnamangalam", "Kunnumal", "Kuruvattur",
            "Kuttiadi", "Madavoor", "Maniyur", "Maruthomkara", "Mavoor",
            "Meppayur", "Moodadi", "Nadapuram", "Naduvannur", "Nanmanda",
            "Narikunni", "Naripetta", "Nochad", "Olavanna", "Omassery",
            "Onchiyam", "Panangad", "Perambra", "Perumanna", "Peruvayal",
            "Purameri", "Puthuppady", "Thalakulathur", "Thamarasseri", "Thikkodi",
            "Thiruvallur", "Thiruvambadi", "Thuneri", "Thurayur", "Uliyeri",
            "Unnikulum", "Valayam", "Vanimel", "Velom", "Villiyappally"
        ],
        "municipality": ['Feroke', 'Koduvally', 'Koyilandy', 'Payyoli', 'Ramanattukara', 'Vatakara'],
        "corporation": ['Kozhikode'],
    },
    "Malappuram": {
        "grama_panchayat": [
            "Abdul Rahiman Nagar", "Alamcode", "Aliparamba", "Amarambalam", "Anakkayam",
            "Angadipuram", "Areekode", "Athavanad", "Chaliyar", "Chekkode",
            "Chelambra", "Cheriyamundam", "Cherukavu", "Chokkad", "Chungathara",
            "Edakkara", "Edappal", "Edappatta", "Edarikode", "Edavanna",
            "Edayoor", "Elamkulam", "Irimbilayam", "Kalady", "Kalikavu",
            "Kalpakancheri", "Kannamangalam", "Karulai", "Karuvarakundu", "Kavannur",
            "Keezhattur", "Kizhuparamba", "Kodur", "Koottilangadi", "Kuruva",
            "Kuttippuram", "Kuzhimanna", "Makkaraparamba", "Mambad", "Mangalam",
            "Mankada", "Marakkara", "Marancheri", "Melattur", "Moonniyur",
            "Moorkkanad", "Moothadem", "Morayur", "Muduvalur", "Nannambra",
            "Nannamukku", "Niramaruthoor", "Othukkungal", "Ozhur", "Pallikkal",
            "Pandikkad", "Parappur", "Perumannaklari", "Perumpadappa", "Peruvallur",
            "Ponmala", "Ponmundam", "Pookkottur", "Porur", "Pothukkal",
            "Pulamanthole", "Pulikkal", "Pulpatta", "Purathur", "Puzhakkattiri",
            "Tanalur", "Tavanur", "Thalakkad", "Thazhekode", "Thenhippalam",
            "Thennala", "Thirunavaya", "Thiruvali", "Thuvvur", "Trikkalangode",
            "Triprangode", "Urakam", "Urungattiri", "Valavannur", "Vallikkunnu",
            "Vattamkulam", "Vazhakkad", "Vazhayur", "Vazhikkadavu", "Veliyancode",
            "Vengara", "Vettathur", "Vettom", "Wandoor"
        ],
        "municipality": ['Kondotty', 'Kottakkal', 'Malappuram', 'Manjeri', 'Mukkom', 'Nilambur', 'Parappanangadi', 'Perinthalmanna', 'Ponnani', 'Tanur', 'Tirur', 'Tirurangadi', 'Valanchery'],
        "corporation": [],
    },
    "Palakkad": {
        "grama_panchayat": [
            "Agali", "Akathethara", "Alanallur", "Alathur", "Ambalapara",
            "Anakkara", "Ananganadi", "Ayiloor", "Chalavara", "Chalisseri",
            "Elappully", "Elavancherry", "Erimayur", "Eruthampathy", "Kadampazhipuram",
            "Kanjirampuzha", "Kannadi", "Kannambara", "Kappur", "Karakurissi",
            "Karimba", "Karimpuzha", "Kavasery", "Keralassery", "Kizhakkancherry",
            "Kodumba", "Koduvayur", "Kollengode", "Kongad", "Koppam",
            "Kottappadam", "Kottayi", "Kozhinjampara", "Kulukkallur", "Kumaramputhur",
            "Kuthanoor", "Kuzhalmannam", "Lakkidiperur", "Malampuzha", "Mankara",
            "Mannur", "Marutharode", "Mathur", "Melarcode", "Mundur",
            "Muthalamada", "Muthuthala", "Nagalassery", "Nalleppilly", "Nellaya",
            "Nelliampathy", "Nemmara", "Ongallur", "Pallassana", "Parli",
            "Parudur", "Pattencherry", "Pattithara", "Peringottukurissi", "Perumatty",
            "Peruvemba", "Pirayari", "Polpully", "Pookkottukavu", "Puducode",
            "Puduppariyaram", "Pudur", "Pudusseri", "Puthunagaram", "Sholayar",
            "Sreekrishnapuram", "Tachampara", "Tarur", "Thachanattukara", "Thenkara",
            "Thenkurissi", "Thirumittacode", "Thiruvegapuram", "Thrikkadeeri", "Thrithala",
            "Vadakarapathy", "Vadakkancheri", "Vadavannur", "Vallapuzha", "Vandazhy",
            "Vaniamkulam", "Vellinezhi", "Vilayur"
        ],
        "municipality": ['Cherpulassery', 'Chittur-Thathamangalam', 'Mannarkad', 'Ottappalam', 'Palakkad', 'Pattambi', 'Shoranur'],
        "corporation": [],
    },
    "Pathanamthitta": {
        "grama_panchayat": [
            "Anicadu", "Aranmula", "Aruvapulam", "Ayiroor", "Chenneerkara",
            "Cherukole", "Chittar", "Elanthoor", "Enadimangalam", "Erathu",
            "Eraviperoor", "Ezhamkulam", "Ezhumattoor", "Kadampanadu", "Kadapra",
            "Kalanjoor", "Kallooppara", "Kaviyoor", "Kodumon", "Koipuram",
            "Konni", "Kottanadu", "Kottangal", "Kozhencherry", "Kulanada",
            "Kunnathanam", "Kuttoor", "Malayalapuzha", "Mallappally", "Mallapuzhassery",
            "Mezhuveli", "Mylapra", "Naranamoozhy", "Naranganam", "Nedumpuram",
            "Niranam", "Omallur", "Pallickal", "Pandalam Thekkekara", "Peringara",
            "Pramadom", "Puramattom", "Ranni", "Ranni Angadi", "Ranni Pazhavangadi",
            "Ranni Perunad", "Seethathodu", "Thannithodu", "Thottapuzhassery", "Thumpamon",
            "Vadasserikkara", "Vallicode", "Vechuchira"
        ],
        "municipality": ['Adoor', 'Pandalam', 'Pathanamthitta', 'Thiruvalla'],
        "corporation": [],
    },
    "Thiruvananthapuram": {
        "grama_panchayat": [
            "Amboori", "Anad", "Andoorkonam", "Anjuthengu", "Aruvikkara",
            "Aryanad", "Aryancode", "Athiyannoor", "Azhoor", "Balaramapuram",
            "Chemmaruthy", "Chenkal", "Cherunniyoor", "Chirayinkeezhu", "Edava",
            "Elakamon", "Kadakkavoor", "Kadinamkulam", "Kallara", "Kallikkadu",
            "Kalliyoor", "Kanjiramkulam", "Karakulam", "Karavaram", "Karode",
            "Karumkulam", "Kattakkada", "Kilimanoor", "Kizhuvilam", "Kollayil",
            "Kottukal", "Kulathoor", "Kunnathukal", "Kuttichal", "Madavoor",
            "Malayinkeezh", "Manamboor", "Mangalapuram", "Manickal", "Maranalloor",
            "Mudakkal", "Nagaroor", "Nanniyode", "Navaikulam", "Nellanad",
            "Ottasekharamangalam", "Ottoor", "Pallichal", "Pallickal", "Panavoor",
            "Pangode", "Parassala", "Pazhayakunnummel", "Peringamala", "Perumkadavila",
            "Poovachal", "Poovar", "Pothencode", "Pulimath", "Pullampara",
            "Thirupuram", "Tholicode", "Uzhamalackal", "Vakkom", "Vamanapuram",
            "Vellanad", "Vellarada", "Vembayam", "Venganoor", "Vettoor",
            "Vilappil", "Vilavoorkkal", "Vithura"
        ],
        "municipality": ['Attingal', 'Nedumangad', 'Neyyattinkara', 'Varkala'],
        "corporation": ['Thiruvananthapuram'],
    },
    "Thrissur": {
        "grama_panchayat": [
            "Adat", "Alagappa Nagar", "Alur", "Annamanada", "Anthicad",
            "Arimpoor", "Athirappally", "Avanur", "Avinissery", "Chazhoor",
            "Chelakkara", "Cherpu", "Choondal", "Chowwannur", "Desamangalam",
            "Edathiruthy", "Edavilangu", "Elavally", "Engandiyur", "Eriyad",
            "Erumapetty", "Kadangode", "Kadappuram", "Kadavallur", "Kadukutty",
            "Kaipamangalam", "Kaiparamba", "Kandanassery", "Karalam", "Kattakampal",
            "Kattur", "Kodakara", "Kodassery", "Kolazhy", "Kondazhy",
            "Koratty", "Kuzhur", "Madakkathara", "Mala", "Manallur",
            "Mathilakam", "Mattathur", "Melur", "Mulakunnathukavu", "Mullassery",
            "Mullurkara", "Muriyad", "Nadathara", "Nattika", "Nenmenikkara",
            "Orumanayur", "Padiyur", "Pananchery", "Panjal", "Paralam",
            "Parappukkara", "Pariyaram", "Pavaratty", "Pazhayannur", "Perinjanam",
            "Poomangalam", "Porkulam", "Poyya", "Pudukkad", "Punnayur",
            "Punnyurkulum", "Puthenchira", "Puthur", "Sree Narayanapuram", "Thalikulam",
            "Thanniyam", "Thekkumkara", "Thiruvilwamala", "Tholur", "Trikkur",
            "Vadanappilly", "Vadekkekad", "Valappad", "Vallachira", "Vallathol Nagar",
            "Varandarappilly", "Varavoor", "Vellangallur", "Vellookkara", "Velur",
            "Venkitangu"
        ],
        "municipality": ['Chalakudy', 'Chavakkad', 'Guruvayoor', 'Irinjalakuda', 'Kodungallur', 'Kunnamkulam', 'Wadakkanchery'],
        "corporation": ['Thrissur'],
    },
    "Wayanad": {
        "grama_panchayat": [
            "Ambalavayal", "Edavaka", "Kaniambetta", "Kottathara", "Meenangadi",
            "Meppadi", "Mullankolly", "Muppainadu", "Muttil", "Nenmeni",
            "Noolpuzha", "Padinharethara", "Panamaram", "Poothadi", "Pozhuthana",
            "Pulpalli", "Thariyode", "Thavinhal", "Thirunelly", "Thondernad",
            "Vellamunda", "Vengappally", "Vythiri"
        ],
        "municipality": ['Kalpetta', 'Mananthavady', 'Sulthanbathery'],
        "corporation": [],
    },
}


def get_districts():
    return sorted(KERALA_LOCAL_BODIES.keys())


def get_local_bodies(district: str, local_body_type: str):
    """
    Returns sorted list of local bodies for a district and type.
    local_body_type: 'grama_panchayat' | 'municipality' | 'corporation'
    """
    district_data = KERALA_LOCAL_BODIES.get(district, {})
    return sorted(district_data.get(local_body_type, []))


def validate_local_body(district: str, local_body_type: str, local_body: str) -> bool:
    """Check if a local body exists in the dataset."""
    return local_body in get_local_bodies(district, local_body_type)
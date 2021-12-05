
import socket # for socket
import sys
import zlib # crc 32
import os

#TODO opravenie posledneho paketu na teste neuspesnych

def print_menu():
    print("-----------------------------------------")
    print("Vyberte s ktorou stranou chcete pracovať:")
    print("1 - SERVER")
    print("2 - KLIENT")
    print("3 - KONIEC")
    print("VLOŽ ČÍSLO: ")

# Funkcia na vytvorenie inicializacnej hlavicky keď klient chce odoslať prvý paket
'''
DRUH SPRAVY:
    7 - keep alive paket
    3 - ukončenie spojenia
    5 - inicializacia bola úspešná 
    6 - fragmentacia nazvu suboru 
    2 - sprava bola dorucena SPRAVNE 
    4 - sprava bola dorucena NESPRAVNE 
    1 - inicializacna hlavicka pre subor
    0 - inicializacna hlavicka pre text
'''

def vytvorenie_inicializacnej_hlavicky(druh_spravy,pocet_fragmentov = 0):

    hlavicka = druh_spravy.to_bytes(1,"big") + pocet_fragmentov.to_bytes(4,"big")

    return hlavicka

def vytvorenie_hlavicky(druh_spravy,poradie_fragmentu,crc):
    hlavicka = druh_spravy.to_bytes(1,"big") + poradie_fragmentu.to_bytes(4,"big") + crc.to_bytes(4,"big")

    return hlavicka

def odpoved_servera(druh_spravy):
    hlavicka = druh_spravy.to_bytes(1,"big")
    return  hlavicka

def vypocet_fragmentu(message,velkost_fragmentu):
    if (len(message) % velkost_fragmentu == 0):
        pocet_fragmentov = int(len(message) / velkost_fragmentu)
    else:
        pocet_fragmentov = int(len(message) / velkost_fragmentu) + 1

    return pocet_fragmentov

def decodovanie_hlavicky_sprava(data):
    druh_spravy = int.from_bytes(data[0:1], "big")
    poradie_paketu = int.from_bytes(data[1:5], "big")
    crc = int.from_bytes(data[5:9], "big")
    data = data[9::]

    return druh_spravy,poradie_paketu,crc,data

def decodovanie_hlavicky_subor_inicializacna(data):
    druh_spravy = int.from_bytes(data[0:1], "big")
    poradie_paketu = int.from_bytes(data[1:5], "big")
    pocet_fragmentov = int.from_bytes(data[5:9], "big")
    data = data[9::]

    return druh_spravy,poradie_paketu,pocet_fragmentov,data


def decodovaie_druh_spravy(data):
    druh_spravy = int.from_bytes(data[0:1], "big")
    return druh_spravy



#tu za prijme inicializačný packet
def inicializacia_servera(port):
    nazov_suboru = ""
    inicializacne_pakety = 0
    pocet_fragmentov_subor_fragmentacia = 1
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    print("Priebieha štart servera...")
    # nastavenie portu
    server_socket.bind(("", int(port)))
    print("SERVER POČÚVA NA PORTE " + str(port))
    pocet_odoslany_paketov_server = 0

    while True:
        data, server_destination_adress = server_socket.recvfrom(1500)
        inicializacne_pakety += 1
        if (decodovaie_druh_spravy(data)==0):
            message_back = vytvorenie_inicializacnej_hlavicky(5) # SPRAVA OK
            pocet_fragmentov = int.from_bytes(data[1:5],"big")
            pocet_odoslany_paketov_server += 1
            server_socket.sendto(message_back, (server_destination_adress))
            print("-- Prišla inicializačná hlavička: SPRAVA | Počet fragmentov prenosu: " + str(pocet_fragmentov))
            server_functionality(server_socket,port,pocet_fragmentov,0,False,"",inicializacne_pakety,pocet_odoslany_paketov_server)



        if(decodovaie_druh_spravy(data)==1):
            message_back = odpoved_servera(2)
            pocet_fragmentov = int.from_bytes(data[1:5], "big")
            pocet_fragmentov_subor_fragmentacia = int.from_bytes(data[5:9], "big")
            pocet_odoslany_paketov_server += 1
            server_socket.sendto(message_back, (server_destination_adress))
            print("-- Prišla inicializačná hlavička: SUBOR | Počet paketov prenosu: " +
                  str(pocet_fragmentov) + "| pocet paketov inicializacneho prenosu: " +
                  str(pocet_fragmentov_subor_fragmentacia))
            nazov_suboru = ""

        if(decodovaie_druh_spravy(data) == 3):
            print(" < --- KLIENT UKONČIL SPOJENIE ")
            ukoncenie = str(input("Pre ukončenie spojenia stlačte y"))
            server_socket.close()
            return

        if(decodovaie_druh_spravy(data) == 6):
            print("------ Primam časti cesta + nazov ")
            druh_spravy, poradie_paketu, crc, data = decodovanie_hlavicky_sprava(data)


            crc_sprava_typ = zlib.crc32(data)
            print("------ DRUH: " + str(druh_spravy) + " PORADIE: " + str(poradie_paketu) +" CRC: " + str(crc))
            print("------ DATA: " + str(data))

            if(crc_sprava_typ ==crc):
                print("CRC OK ")

            nazov_suboru += str(data.decode("utf-8"))

            if(pocet_fragmentov_subor_fragmentacia == poradie_paketu):

                message_back = vytvorenie_inicializacnej_hlavicky(5)
                pocet_odoslany_paketov_server += 1
                server_socket.sendto(message_back, (server_destination_adress))
                server_functionality(server_socket,port,pocet_fragmentov,0,True,nazov_suboru,inicializacne_pakety,pocet_odoslany_paketov_server)
            else:
                message_back = vytvorenie_inicializacnej_hlavicky(2)
                pocet_odoslany_paketov_server += 1
                server_socket.sendto(message_back, (server_destination_adress))



def inicializacia_clienta(adresa, port):


    fragmenty_na_odoslanie = [ ]
    fragmenty_na_odoslanie_inicializacny = []
    cesta_obrazok_odoslanie = ""
    message = ""

    inicializacne_pakety = 0


    # Potrebné vstupy na začiatok klienta

    # 1500 - 20(IP HLAVIČKA) - (8 BI UDP hlavička) -  9 B - [ DATA ]   = 1463 !!
    velkost_fragmentu = int(input("Velkost fragmentu: [MAX: 1463]"))

    #message = b"Islovajconavandrovkuastretlojozapidika "
    input_typ = (str(input("typ odosielanej spravy m - text f - subor ")))


    if (input_typ == 'f'):
        cesta_obrazok_odoslanie = str(input("Zadaj cestu k obrazku"))
        print("CELA CESTA OBRAZKU NA ODOSLANIE: " + str(cesta_obrazok_odoslanie))
        with open(cesta_obrazok_odoslanie, "rb") as f:
            message = f.read()
            cesta_obrazok_odoslanie = os.path.basename(cesta_obrazok_odoslanie)
    else:
        message = str(input("Zadaj spravu ktoru chces poslat"))
        message = message.encode()


    pocet_fragmentov = vypocet_fragmentu(message,velkost_fragmentu)

    # Rozdelenie správy do jednotlivých fragmentov

    for seq in range(0,len(message),velkost_fragmentu):
        #print(message[int(seq):int(seq)+velkost_fragmentu])
        fragmenty_na_odoslanie.append(message[int(seq):int(seq)+velkost_fragmentu])


    fragmenty_na_odoslanie = fragmenty_na_odoslanie[::-1]

    print("FRAGMENTY NA ODOSLANIE:")
    print(fragmenty_na_odoslanie)

    # Len overenie
    if(len(fragmenty_na_odoslanie) == (pocet_fragmentov)):
        print("check fragmenty == pocet fragmentov | OK")
    else:
        print("check fragmenty == pocet fragmentov | ERROR")


    # Vytvorenie inicializačnej hlavičky

    if (input_typ == "f"):
        pocet_fragmentov_typsuboru = vypocet_fragmentu(cesta_obrazok_odoslanie, velkost_fragmentu)
        hlavicka = vytvorenie_inicializacnej_hlavicky(1,pocet_fragmentov) + pocet_fragmentov_typsuboru.to_bytes(4,"big")
    else:
        hlavicka = vytvorenie_inicializacnej_hlavicky(0, pocet_fragmentov)

    packet = hlavicka

    # Vytvorenie socketu



    client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    # Poslanie prvého inicializačného packetu na server

    client_socket.sendto(packet, (adresa, port))

    data, client_destination_adress_port = client_socket.recvfrom(1500)

    # Fragmentacia nazvu suboru

    if(input_typ == 'f'):
        if (len(cesta_obrazok_odoslanie) > velkost_fragmentu):
            print("INICIALIZAČNU HLAVIČKU TREBA FRAGMENTOVAŤ")



            # Rozdelenie správy do jednotlivých fragmentov

            for seq in range(0, len(cesta_obrazok_odoslanie), velkost_fragmentu):
                print(cesta_obrazok_odoslanie[int(seq):int(seq) + velkost_fragmentu])
                fragmenty_na_odoslanie_inicializacny.append(cesta_obrazok_odoslanie[int(seq):int(seq) + velkost_fragmentu])

            fragmenty_na_odoslanie_inicializacny = fragmenty_na_odoslanie_inicializacny[::-1]

            print("FRAGMENTY NA ODOSLANIE V INICIALIZACNEJ SPRAVE:")

            print(fragmenty_na_odoslanie_inicializacny)

            poradie_fragmentu_server = 0
            if(int.from_bytes(data[0:1],"big") == 2): #refaktor
                while len(fragmenty_na_odoslanie_inicializacny) > 0:
                    poradie_fragmentu_server += 1
                    fragment_subor = fragmenty_na_odoslanie_inicializacny.pop()
                    fragment_subor = fragment_subor.encode()
                    crc_typ = zlib.crc32(fragment_subor)
                    print(" --> ODOSIELAM | typ spravy :" + str(6) +
                          " poradie_fragmentu: " + str(poradie_fragmentu_server) +
                          " pocet_fragmentov: " + str(crc_typ))

                    client_socket.sendto(vytvorenie_hlavicky(6,poradie_fragmentu_server,crc_typ) + fragment_subor, (adresa, port))
                    data, client_destination_adress_port = client_socket.recvfrom(1500)

                    print("<--- POTVRDENIE : " + str(int.from_bytes(data[0:1],"big")))


                    if(int.from_bytes(data[0:1],"big") == 5):
                        print("NAZOV SUBORU USPEŠNE INICIALIZOVANY")
                        break
        else:
            print("HLAVIČKA BEZ FRAGMENTACIE")
            client_socket.sendto(vytvorenie_hlavicky(6, 1, 1) + cesta_obrazok_odoslanie.encode(),(adresa, port))
            data, client_destination_adress_port = client_socket.recvfrom(1500)
            print("**** PRIŠLO  SPRAVA OK ")
            print(int.from_bytes(data[0:1], "big"))




    print("------ INICIALIZÁCIA HODNOT SKONČILA -----------")

    if(int.from_bytes(data[0:1],"big") == 5):
        print("SERVER POTVRDIL INICIALIZACIU - inicializácia správa ! druh spravy [ 5 = INICIALIZACIA USPESNA ] ")
        client_functionality(client_socket,adresa,port,fragmenty_na_odoslanie,pocet_fragmentov,velkost_fragmentu)
    else:
        print("ERROR !!!!  - server nepotrvrdil inicializáciu ")


def server_functionality(server_socket,port,pocet_fragmentov,crc,subor_prijma = False,nazov_suboru = "",inicializacne_pakety = 0,pocet_odoslany_paketov_server = 0):

    print("*******************************************")
    print("********* SERVER IDE PRIJMAT DATA *********")
    print("*******************************************")

    prijata_sprava = b""

    uspesne_prijata = 0
    neuspesne_prijata = 0

    while True:
        data, server_destination_adress = server_socket.recvfrom(1500)

        druh_spravy, poradie_paketu, crc, data_fragmentu = decodovanie_hlavicky_sprava(data)


        print("******************************\nTYP SPRAVY: " + str(druh_spravy)+ " PORADIE: " + str(poradie_paketu) + " CRC: " + str(crc))
        #print(data_fragmentu.decode())



        if(druh_spravy == 1 or druh_spravy == 2):
            crc_sprava = zlib.crc32(data_fragmentu)

            if (crc == crc_sprava):
                print("CRC OK")
                pocet_odoslany_paketov_server += 1
                server_socket.sendto(odpoved_servera(2), (server_destination_adress))
                prijata_sprava += data_fragmentu
                uspesne_prijata += 1
            else:
                print("CRC FALSE - odosielam poziadavku o znovuzaslanie spravy ")
                neuspesne_prijata +=1
                pocet_odoslany_paketov_server += 1
                server_socket.sendto(odpoved_servera(4), (server_destination_adress))
                if(pocet_fragmentov == poradie_paketu):
                    data, server_destination_adress = server_socket.recvfrom(1500)
                    druh_spravy, poradie_paketu, crc, data_fragmentu = decodovanie_hlavicky_sprava(data)
                    crc_sprava = zlib.crc32(data_fragmentu)
                    if (crc == crc_sprava):
                        print("CRC OK")
                        pocet_odoslany_paketov_server += 1
                        server_socket.sendto(odpoved_servera(2), (server_destination_adress))
                        prijata_sprava += data_fragmentu
                        uspesne_prijata += 1

            if(pocet_fragmentov == poradie_paketu):
                break


    if(subor_prijma):
        print("---------------------------------------")

        print("NAZOV SUBORU :" + str(nazov_suboru))
        cesta_k_suboru = str(input("Zadaj cestu kam sa má subor uložiť"))
        final_cesta = str(cesta_k_suboru + nazov_suboru)
        print("CELA CESTA: " + final_cesta)

        with open(final_cesta, "wb") as f:
            f.write(prijata_sprava)
            f.close()

    print("//////////////// VYSLEDKY /////////////////")
    print("CELA PRIJATA SPRAVA: ")
    print(prijata_sprava)
    print("USPESNE PRIJATYCH: " +
          str(uspesne_prijata + inicializacne_pakety) +
          " NEUSPESNE: " + str(neuspesne_prijata) +
          " VSETKY: " + str(uspesne_prijata + neuspesne_prijata +inicializacne_pakety))
    print("Z TOHO POCET INICIALIZACNYCH PAKETOV " + str(inicializacne_pakety))
    print("SERVER ODOSLAL: " + str(pocet_odoslany_paketov_server))
    print("UPLNE VŠETKY PRENESENE PAKETY: " + str(uspesne_prijata + neuspesne_prijata +inicializacne_pakety +pocet_odoslany_paketov_server ) )

def client_functionality(client_socket,adresa,port,fragmenty_na_odoslanie,pocet_fragmentov,velkost_fragmentu):

    print("*** KLIENT IDE ODOSIELAT DATA ***")
    print("DATA NA ODOSLANIE: " + str(fragmenty_na_odoslanie))

    simulacia_chyba = str(input("SIMULACIA CHYBY ? y/n"))
    pocet_zlych_paketov= int(input("Zadaj počet zlych paketovu"))
    array_zlych_paketov = []

    if (simulacia_chyba == 'y'):
        for x in range(pocet_zlych_paketov):
            array_zlych_paketov.append(int(input("Zadaj č. paketu")))

    poradie = 0

    while len(fragmenty_na_odoslanie) > 0:
        poradie += 1

        fragment = fragmenty_na_odoslanie.pop()

        crc = zlib.crc32(fragment)

        if simulacia_chyba == "y" and (poradie in array_zlych_paketov):
            crc = zlib.crc32(b"zlaspravauplne")
            poradie_zlych = array_zlych_paketov.index(poradie)
            array_zlych_paketov.pop(poradie_zlych)


        print(" --> ODOSIELAM paket  č. " + str(poradie) + " velkost fragmentu " + str(velkost_fragmentu) + " CRC " + str(crc))
        client_socket.sendto((vytvorenie_hlavicky(2,poradie,crc) + fragment),(adresa,port))

        data, server_destination_adress = client_socket.recvfrom(1500)

        druh_spravy, poradie_paketu, crc, data_fragmentu = decodovanie_hlavicky_sprava(data)

        if(druh_spravy == 2):
            print(" <--- PORVRDENIE OK : "+ str(druh_spravy))
        else:
            poradie -= 1
            print(" <--- ERROR !! Sprava prišla zlá pošli fragmant spať do pola")
            if (len(fragmenty_na_odoslanie)==0):
                client_socket.sendto((vytvorenie_hlavicky(2, poradie, crc) + fragment), (adresa, port))
                druh_spravy, poradie_paketu, crc, data_fragmentu = decodovanie_hlavicky_sprava(data)
                if (druh_spravy == 2):
                    print(" <--- PORVRDENIE OK : " + str(druh_spravy))

            fragmenty_na_odoslanie.append(fragment)




    print("** VSETKY DATA BOLI ODOSLANÉ ")
    print("Ukončiť spojenie ? ")
    ukoncenie_spojenia = str(input("y/n ?"))

    if(ukoncenie_spojenia == 'y'):
        client_socket.sendto((vytvorenie_inicializacnej_hlavicky(3, 1)), (adresa, port))
        client_socket.close()



if __name__ == '__main__':


    zadat_ip = True
    pokracovat = 'y'

    while True:
        print_menu()
        menu_input = int(input())
        if(menu_input == 1):
            inicializacia_servera(1)

        if (menu_input == 2):

            if(pokracovat == 'y'):
                adresa = str(input("Zadanie IP adresy"))
                port = int(input("Zadanie portu"))
                while True:
                    inicializacia_clienta(adresa,port)
                    print("CHCETE ODOSLAŤ DALŠIU SPRAVU ? y/n ")
                    pokracovat = str(input())
                    if(pokracovat == 'n'):
                        break

        if(menu_input == 3):
            print("Ukončujem program")
            break



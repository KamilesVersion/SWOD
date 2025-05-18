# S.W.O.D.
Komandinis projektas "S.W.O.D.".

# Komandos nariai

Projektą kūrė KTU IFA-3/1 grupės nariai: 
- Ieva Šalašavičiūtė
- Kamilė Vaškytė
- Laurynas Zavjalovas
- Emilija Budinaitė

# Techninė užduotis 

Šio projekto tikslas yra sukurti "S.W.O.D", Spotify statistikos tinklalapio programą naudojant Python, Visual Studio aplinkoje. Pagrindinė projekto užduotis yra pasinaudojant naudotojo Spotify duomenimis išvesti įvairią klausymosi statistiką.
Projekto valdymui ir komandos darbui naudota "Jira", bendravimui "Discord" platforma.

# Testavimas

| Testuojamas funkcionalumas                                              | Rezultatas, kurio tikimasi                                                                                                                                                                                                                                                        | Gautas rezultatas                                                                                                                                                                                                                                                                                                     |
|-------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Top atlikėjo klausymo laikas                                            | Pagrindiniame puslapyje mėgstamiausio atlikėjo blokelyje turėtų matytis laikas minutėmis, kiek šio atlikėjo buvo klausytasi.                                                                                                                                                      | Pagrindiniame puslapyje mėgstamiausio atlikėjo blokelyje prie pavadinimo matomas laikas minutėmis, kiek šio atlikėjo buvo klausytasi.                                                                                                                                                                                 |
| Paros metas, kada klausoma dažniausiai per pasirinktą laiko intervalą   | Pasirinkto intervalo apžvalgos puslapyje turėtų būti matomas paros metas, kada buvo daugiausiai klausytasi muzikos per tą intervalą, ir skritulinė diagrama, atvaizduojanti visų paros meto variantų pasiskirstymą per laiko intervalą.                                           | Pasirinkto intervalo apžvalgos puslapyje matomas blokelis, kuriame parašytas paros metas, kada klausytasi daugiausiai, ir kiek dainų buvo klausyta tuo metu. Po juo yra kitas blokelis su skrituline diagrama, kurioje atvaizduojamas pilnas klausymo pasiskirstymas pagal paros metą per pasirinktą laiko intervalą. |
| Paros metas, kada klausoma dažniausiai per visą laiką nuo registracijos | Pagrindiniame puslapyje po jau esančiais blokeliais turėtų būti dar du nauji blokeliai. Viename turi būti užrašytas paros metas, kada buvo klausytasi muzikos daugiausiai. Kitame blokelyje turi būti atvaizduota skritulinė diagrama su visų paros metų pasiskirstymu.           |  Pagrindiniame puslapyje po buvusiais blokeliais yra dar du nauji. Pirmajame matomas paros laikas, kai buvo daugiausiai klausomasi muzikos. Antrajame blokelyje yra skritulinė diagrama vaizduojanti klausymosi pasiskirstymą pagal paros metus.                                                                      |
| Albumą rikiuojanti funkcija                                             | Albumo rikiavimo puslapyje, kuris randamas paspaudus "sort an album" mygtuką esantį šono meniu punkte, įvedus atlikėjo vardą ir pasirinkus jo albumą, turėtu būti  matomas surikiuotas albumas pagal dainų klausymo kiekį.                                                        | Paspaudus reikiamą mygtuką atsidaro puslapis, kuriame pasirinkus atlikėjo pavadinimą ir tada albumą metamas surikiuotas albumas pagal individualių dainų klausymo kiekį, pasirinkto albumo nuotrauka ir pavadinimas bei originalus albumo tracklist'as palyginimui su rikiuotu.                                       |
| Mygtukas atgal į žanrų puslapį, iš atlikėjų pagal žanrą puslapio        | Atlikėjų pagal pasirinktą žanrą puslapyje, paspaudus mygtuką " ← back to genres" naudotojas turėtų būti nukeliamas atgal į savo klausomų žanrų puslapį.                                                                                                                           | Atlikėjų pagal pasirinktą žanrą puslapyje, paspaudus mygtuką " ← back to genres" naudotojas yra nukeliamas atgal į savo klausomų žanrų puslapį.                                                                                                                                                                       |
| Top 5 mėnesio atlikėjai                                                 | Mėnesio apžvalgos puslapyje turėtų būti matomas sąrašas su labiausiai klausytais atlikėjais per paskutines 30 dienų. Turėtų būti matomas atlikėjo vardas, jo klausymų skaičius per tą mėnesį, jo nuotrauka.                                                                       | Mėnesio apžvalgos puslapyje yra matomas sąrašas su 5 daugiausiai klausytais atlikėjais (vardas, nuotrauka ir klausymo kiekis) per 30 paskutinių dienų.                                                                                                                                                                |
| Top 10 mėnesio dainų                                                    | Mėnesio apžvalgos puslapyje turėtų būti matomas sąrašas su labiausiai klausytomis dainomis per paskutines 30 dienų. Turėtų būti matoma viršelio nuotrauka, dainos pavadinimas, atlikėjas, kiek kartų buvo klausyta šios dainos per mėnesį ir laikas minutėmis kiek buvo klausyta. | Mėnesio apžvalgos puslapyje matomas sąrašas su labiausiai klausytomis dainomis (viršelio nuotrauka, dainos pavadinimas, dainos atlikėjas, kiek kartų buvo klausyta šios dainos per mėnesį ir laikas minutėmis kiek buvo klausyta) per paskutines 30 dienų.                                                            |
| Top mėnesio albumas                                                     | Mėnesio apžvalgos puslapyje turėtų būti matomas labiausiai per 30 paskutinių dienų klausyto albumo viršelis, pavadinimas, atlikėjas, klausymų kiekis kartais bei laikas minutėmis.                                                                                                | Mėnesio apžvalgos puslapyje matomas labiausiai per 30 paskutinių dienų klausyto albumo viršelis, pavadinimas, atlikėjas, klausymų kiekis kartais bei laikas minutėmis.                                                                                                                                                |
| Paros metas, kada klausoma dažniausiai per mėnesį                       | Mėnesio apžvalgos puslapyje turėtų būti matomas laikas, kada buvo klausoma muzikos daugiausiai per paskutines 30 dienų. Taip pat turėtų būti matoma skritulinė diagrama atvaizduojanti klausymo laiko pasiskirstymą skirtingais paros laikais.                                    | Mėnesio apžvalgos puslapyje matomas laikas, kada buvo klausoma muzikos daugiausiai per paskutines 30 dienų, matoma skritulinė diagrama atvaizduojanti klausymo laiko pasiskirstymą skirtingais paros laikais.                                                                                                         |
| Sukurti grojaraščių puslapį                                             | Meniu juostoje turėtų būti mygtukas , kuris nuveda į puslapį, kuriame generuos grojaraščius. Tas puslapis turi turėti įprastus tinklalapio CSS bruožus, jokio funkcionalumo.                                                                                                      | Meniu juostoje matomas mygtukas ,kuris nuveda į puslapį, kuriame generuos grojaraščius. Puslapis turi visus įprastus CSS bruožus, jokio funkcionalumo.                                                                                                                                                                |
| Sukurti grojaraščių pasirinkimus                                        | Grojaraščių puslapyje turi atsirasti trys veikiantys mygtukai: "Top 20 Songs", "Recent 20 Songs" ir "Top 20 This Week". Paspaudus juos, turi susigeneruoti "Spotify" grojaraščiai ir jų nuorodos.                                                                                 | Grojaraščio puslapis nebeveikia, meta "Method Not Allowed. The method is not allowed for the requested URL."                                                                                                                                                                                                          |
| Sukurti grojaraščių pasirinkimus                                        | Grojaraščių puslapyje turi atsirasti trys veikiantys mygtukai: "Top 20 Songs", "Recent 20 Songs" ir "Top 20 This Week". Paspaudus juos, turi susigeneruoti "Spotify" grojaraščiai ir jų nuorodos.                                                                                 | Grojaraščių puslapyje atsirado trys veikiantys mygtukai: "Top 20 Songs", "Recent 20 Songs" ir "Top 20 This Week". Paspaudus juos, susigeneruoja "Spotify" grojaraščiai ir jų nuorodos.                                                                                                                                |
| Sukurti albumo rikiavimo puslapį                                        | Meniu punkte paspaudus "sort an album" mygtuką, turėtų atsidaryti langas su atlikėjo ir jo albumo pasirinkimais.                                                                                                                                                                  | Atidarius atitinkama meniu punktą, matomas puslapis su atlikėjo ir jo albumo pasirinkimu.                                                                                                                                                                                                                             |


# Naudotojo dokumentacija

Nuoroda į tinklalapį:
https://lauzav.pythonanywhere.com

Atsidarius tinklalapį pamatome vaizdą pateiktą 1 pav. Pateikti du pasirinkimai: registracija arba prisijungimas. Pasirinkus vieną iš jų reikia įvesti savo vartotojo vardą ir slaptažodį (registracijos atveju - susikurti). Kuriant slaptažodį būtina panaudoti bent vieną didžiąją raidę, mažąją raidę, skaitmenį, specialųjį simbolį, o iš viso turi būti bent 8 simboliai.

### 1 pav. Autentikavimo puslapis
![image](https://github.com/user-attachments/assets/831eea32-2756-4195-ad6d-4b78e916943a)

Prisijungus patenkama į pagrindinį puslapį (2 pav.). Ten matoma naudotojo viso laiko (nuo registracijos) statistika, o dešinėje matomas meniu. 

### 2 pav. Pagrindinis puslapis
![image](https://github.com/user-attachments/assets/2061d5f2-3be1-471a-b874-1a6f1a990090)

Profilio puslapyje (3 pav.) galima pamatyti paskyros detalias, redaguoti profilį, atsijungti arba ištrinti paskyrą. 

### 3 pav. Profilis 
![image](https://github.com/user-attachments/assets/d5a76c29-5f0d-4ab0-8341-501a488ca2f5)

Meniu skiltyje pasirinkus "ur recaps" naudotojas nukreipiamas į apžvalgų puslapį (4 pav.). Galimi 5 variantai: šiandienos, vakar dienos, praėjusios savaitės, praėjusio mėnesio arba pasirinkto intervalo apžvalga. Pasirinkus paskutinįjį variantą atidaromas puslapis, matomas 5 pav. Pasirinkus norimą intervalą išmetamas puslapis su to intervalo statistika (6 pav.).

### 4 pav. Apžvalgų puslapis
![image](https://github.com/user-attachments/assets/5161172f-ba0a-4954-aa0b-34e6faa057ed)

### 5 pav. Pasirinktinio intervalo apžvalgos puslapis (intervalo pasirinkimas)
![image](https://github.com/user-attachments/assets/c0e77efd-6e00-43e5-8d45-e8901f827e9d)

### 6 pav. Pasirinktinio intervalo apžvalgos puslapis (rezultatai)
![image](https://github.com/user-attachments/assets/23d814c9-cf79-4435-ba5e-80aa776968dd)

Pasirinkus "sort an album" funkciją atidaromas puslapis (7 pav.), kuriame įrašomas atlikėjo pavadinimas ir pasirenkamas norimas albumas iš duotų. Pasirinkus, matomas sąrašas albumo dainų, surikiuotų pagal klausymo kiekį (8 pav.)

### 7 pav. Albumo rikiavimo puslapis (albumo pasirinkimas)
![image](https://github.com/user-attachments/assets/bfd8f3e0-e287-4108-a596-e7aa92bc08b2)

### 8 pav. Albumo rikiavimo puslapis (rezultatas)
![image](https://github.com/user-attachments/assets/9432ac4d-d036-428c-9f5c-550ac528f96f)

Kitos funkcijos:
- "recent tracks" - 20 paskutinių klausytų dainų
- "ur top artists" - 10 daugiausiai klausytų atlikėjų
- "ur top albums" - 10 daugiausiai klausytų albumų
- "ur top songs" - 50 daugiausiai klausytų dainų
- "ur top genres" - klausytų žanrų sąrašas. Paspaudus ant specifinio žanro parodomas sąrašas su to žanro klausytais atlikėjais
- "search by artist" - įrašius norimą atlikėją, pateikiamos 10 daugiausiai klausytų to atlikėjų dainų.
- "generate a playlist" - paspaudus atitinkamą mygtuką, sudaromas viešas grojaraštis Spotify paskyroje. Yra trys pasirinkimo variantai: top 20 dainų, paskutinės 20 dainų, top 20 šios savaitės dainų.





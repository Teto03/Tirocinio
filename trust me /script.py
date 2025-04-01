def estrai_tutti_blocchi(file_input, file_output, etichetta_inizio, etichetta_fine, max_blocchi=2000):
    scrittura = False
    raccolta_testi = []  # Lista per raccogliere tutti i blocchi
    blocco_corrente = []

    with open(file_input, 'r', encoding='utf-8') as fin:
        for linea in fin:
            if etichetta_inizio in linea:
                scrittura = True  # Inizia un nuovo blocco
                blocco_corrente = [etichetta_inizio]  # Include l'etichetta di apertura
                continue
            elif etichetta_fine in linea:
                scrittura = False  # Fine del blocco
                blocco_corrente.append(etichetta_fine)  # Include l'etichetta di chiusura
                raccolta_testi.append("\n".join(blocco_corrente))  # Salva il blocco
                # Interrompi la lettura se hai raggiunto il numero massimo di blocchi
                if len(raccolta_testi) >= max_blocchi:
                    break
                continue
            if scrittura:
                blocco_corrente.append(linea.strip())  # Aggiunge la riga al blocco

    # Limita il numero di blocchi a max_blocchi
    raccolta_testi = raccolta_testi[:max_blocchi]

    # Salva i blocchi limitati nel file di output
    with open(file_output, 'w', encoding='utf-8') as fout:
        fout.write("\n\n--- NUOVO BLOCCO ---\n\n".join(raccolta_testi))  # Divide i blocchi con "---"

    print(f"{len(raccolta_testi)} blocchi estratti e salvati in '{file_output}' (limite: {max_blocchi})")

# Esempio di utilizzo
estrai_tutti_blocchi('2490-out', '2490_Confused.txt', '###CONFUSED###', '###ENDCONFUSED###', 2000)
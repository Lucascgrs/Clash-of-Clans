import os
import time
import json
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import pyautogui
import cv2
import numpy as np
import pytesseract
import re
import dxcam


path = os.path.dirname(os.path.abspath(__file__))
path_actions = path + "\\Actions"


class LecteurPosition:
    def __init__(self, fichier_entree="attaqueptitlulu.json"):
        self.fichier_entree = fichier_entree
        self.souris = MouseController()
        self.clavier = KeyboardController()
        self.actions = []

    def charger_actions(self):
        try:
            with open(self.fichier_entree, 'r') as f:
                data = json.load(f)
                self.actions = data['actions']
                metadata = data['metadata']
                return True
        except Exception as e:
            print(f"Erreur lors du chargement du fichier : {e}")
            return False

    def convertir_bouton(self, nom_bouton):
        if 'left' in nom_bouton.lower():
            return Button.left
        elif 'right' in nom_bouton.lower():
            return Button.right
        elif 'middle' in nom_bouton.lower():
            return Button.middle
        return Button.left

    def convertir_touche(self, nom_touche):
        # Convertit les touches spéciales
        if nom_touche.startswith('Key.'):
            nom_sans_prefixe = nom_touche[4:]
            if hasattr(Key, nom_sans_prefixe):
                return getattr(Key, nom_sans_prefixe)
        return nom_touche

    def rejouer(self, vitesse=1.0):
        if not self.charger_actions():
            return

        # Attendre 3 secondes pour permettre à l'utilisateur de se préparer
        time.sleep(1)

        temps_debut = time.time()
        temps_derniere_action = 0

        try:
            for action in self.actions:
                # Calculer le temps d'attente ajusté par la vitesse
                temps_a_attendre = (action['temps'] - temps_derniere_action) / vitesse
                if temps_a_attendre > 0:
                    time.sleep(temps_a_attendre)

                # Exécuter l'action
                if action['type'] in ['mouvement_souris', 'position_initiale']:
                    self.souris.position = (action['x'], action['y'])

                elif action['type'] == 'clic_souris':
                    self.souris.position = (action['x'], action['y'])
                    bouton = self.convertir_bouton(action['bouton'])
                    if action['presse']:
                        self.souris.press(bouton)
                    else:
                        self.souris.release(bouton)

                elif action['type'] == 'defilement_souris':
                    self.souris.position = (action['x'], action['y'])
                    self.souris.scroll(action['dx'], action['dy'])

                elif action['type'] == 'pression_touche':
                    touche = self.convertir_touche(action['touche'])
                    self.clavier.press(touche)

                elif action['type'] == 'relachement_touche':
                    touche = self.convertir_touche(action['touche'])
                    self.clavier.release(touche)

                temps_derniere_action = action['temps']

            temps_total = time.time() - temps_debut

        except KeyboardInterrupt:
            print("Lecture interrompue par l'utilisateur")


class OCR:
    def __init__(self):
        self.zone_ouvrier = (940, 39, 90, 41)
        self.zone_gold = (1515, 40, 300, 41)
        self.zone_elexir = (1515, 143, 300, 41)

        self.zone_ameliorations = (700, 150, 563, 70)

        self.zone_ameliorations_m1 = (700, 750, 563, 70)
        self.zone_ameliorations_m2 = (700, 700, 563, 70)
        self.zone_ameliorations_m3 = (700, 645, 563, 70)
        self.zone_ameliorations_m4 = (700, 585, 563, 70)
        self.zone_ameliorations_m5 = (700, 525, 563, 70)
        self.zone_ameliorations_m6 = (700, 470, 563, 70)
        self.zone_ameliorations_m7 = (700, 410, 563, 70)
        self.zone_ameliorations_m8 = (700, 350, 563, 70)
        self.zone_ameliorations_m9 = (700, 300, 563, 70)
        self.zone_ameliorations_m10 = (700, 240, 563, 70)
        self.zone_ameliorations_m11 = (700, 180, 563, 70)
        self.dict_zones = {"zm1": self.zone_ameliorations_m1,
                           "zm2": self.zone_ameliorations_m2,
                           "zm3": self.zone_ameliorations_m3,
                           "zm4": self.zone_ameliorations_m4,
                           "zm5": self.zone_ameliorations_m5,
                           "zm6": self.zone_ameliorations_m6,
                           "zm7": self.zone_ameliorations_m7,
                           "zm8": self.zone_ameliorations_m8,
                           "zm9": self.zone_ameliorations_m9,
                           "zm10": self.zone_ameliorations_m10,
                           "zm11": self.zone_ameliorations_m11, }

        self.dict_ameliorations = {}

    def capture_et_ocr(self, region, title=None):
        # Initialize DXcam if not already done
        if not hasattr(self, 'dxcam_camera'):
            self.dxcam_camera = dxcam.create()

        # DXcam expects region as (left, top, right, bottom)
        # Convert from pyautogui format (left, top, width, height)
        left, top, width, height = region
        dxcam_region = (left, top, left + width, top + height)

        # Capture screenshot using dxcam
        screenshot = self.dxcam_camera.grab(region=dxcam_region)

        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

        # Apply threshold
        _, thresh = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)

        # Save if title is provided
        if title:
            cv2.imwrite(path + '\\' + title + ".png", thresh)

        # OCR
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(thresh, config=custom_config).strip()
        text = re.sub(r'\n+', '//', text)

        return text

    def get_nb_free_workers(self):
        try:
            s = self.capture_et_ocr(self.zone_ouvrier).strip().replace('o', '0').replace('O', '0')
            if '/' in s:
                self.nb_ouvriers = s.split('/')[0]
            else:
                self.nb_ouvriers = s[0]
        except:
            self.nb_ouvriers = 0

        print(self.nb_ouvriers, " free workers")
        return self.nb_ouvriers

    def get_gold_and_elexir(self):
        gold_str = self.capture_et_ocr(self.zone_gold, "gold").replace('o', '0').replace('O', '0')
        gold_digits = re.sub(r'\D', '', gold_str)  # Enlève tout sauf les chiffres
        self.gold = int(gold_digits) if gold_digits else 0

        elexir_str = self.capture_et_ocr(self.zone_elexir, "elexir").replace('o', '0').replace('O', '0')
        elexir_digits = re.sub(r'\D', '', elexir_str)
        self.elexir = int(elexir_digits) if elexir_digits else 0

        print('gold : ', self.gold, 'elexir : ', self.elexir)
        return self.gold, self.elexir

    def upgrade_wall(self):

        self.get_nb_free_workers()
        self.get_gold_and_elexir()

        if self.nb_ouvriers == 0:
            return

        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\clicinfoouvriers.json").rejouer()
        time.sleep(1)

        cpt = 1
        last = True
        loop = 40
        zone = None
        while cpt <= loop or last:

            if cpt > loop:
                zone = self.dict_zones[f'zm{cpt-loop}']
            else:
                zone = self.zone_ameliorations
                LecteurPosition(fichier_entree=path_actions + "\\infoouvriersuivant.json").rejouer()

            try:
                self.liste_ameliorations = self.capture_et_ocr(zone).split('//')
            except:
                last = False
                break

            for amelioration in self.liste_ameliorations:
                ameliorationsplit = re.sub(r'[^a-zA-Z0-9 ]', '', amelioration).split(' ')
                prix = ''
                nom = ''
                for i in range(len(ameliorationsplit) - 1, -1, -1):
                    if ameliorationsplit[i].isdigit():
                        prix = str(ameliorationsplit[i]) + prix
                    else:
                        nom = ameliorationsplit[i] + nom
                try:
                    prix = int(prix)
                except:
                    prix = 0

                self.dict_ameliorations[nom] = prix

                if 'rempart' in nom.lower():
                    if prix > self.gold and prix > self.elexir:
                        print('Rempart trop cher : ', prix)

                    else:
                        clic_coord = (zone[0] + 50, (zone[1] * 2 + zone[3]) // 2)
                        pyautogui.click(clic_coord[0], clic_coord[1])
                        nb_remparts_a_ameliorer_gold = self.gold // prix
                        nb_remparts_a_ameliorer_elexir = self.elexir // prix
                        print("remparts à améliorer : ", nb_remparts_a_ameliorer_gold + nb_remparts_a_ameliorer_elexir)

                        if nb_remparts_a_ameliorer_gold > 0:
                            LecteurPosition(fichier_entree=path_actions + "\\ameliorerplus.json").rejouer()
                            for r in range(1, nb_remparts_a_ameliorer_gold):
                                LecteurPosition(fichier_entree=path_actions + "\\ajouterrempart.json").rejouer()
                            LecteurPosition(fichier_entree=path_actions + "\\ameliorerrempartgold.json").rejouer()
                            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()

                        if nb_remparts_a_ameliorer_elexir > 0:
                            LecteurPosition(fichier_entree=path_actions + "\\ameliorerplus.json").rejouer()
                            for r in range(1, nb_remparts_a_ameliorer_elexir):
                                LecteurPosition(fichier_entree=path_actions + "\\ajouterrempart.json").rejouer()
                            LecteurPosition(fichier_entree=path_actions + "\\ameliorerrempartelexir.json").rejouer()
                            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()

                        return

            cpt += 1

            print(self.dict_ameliorations)


if __name__ == "__main__":

    for k in range(2):

        LecteurPosition(fichier_entree=path_actions + "\\switchptitlulu.json").rejouer()
        time.sleep(3)
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\selectfirstarmy.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        time.sleep(10)
        for i in range(0):
            LecteurPosition(fichier_entree=path_actions + "\\lose.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        for i in range(20):
            LecteurPosition(fichier_entree=path_actions + "\\attaqueptitlulu.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()

        OCR().upgrade_wall()

        # ----------------------------------------------------

        """LecteurPosition(fichier_entree=path_actions + "\\switchtilu.json").rejouer()
        time.sleep(3)
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\selectfirstarmy.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        time.sleep(1)
        for i in range(8):
            LecteurPosition(fichier_entree=path_actions + "\\lose.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        for i in range(25):
            LecteurPosition(fichier_entree=path_actions + "\\attaquetilu.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()

        LecteurPosition(fichier_entree=path_actions + "\\selectsecondarmy.json").rejouer()
        
        OCR().upgrade_wall()"""

        # ----------------------------------------------------

        LecteurPosition(fichier_entree=path_actions + "\\switchciteor.json").rejouer()
        time.sleep(3)
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\selectfirstarmy.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        time.sleep(1)
        for i in range(5):
            LecteurPosition(fichier_entree=path_actions + "\\lose.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        for i in range(15):
            LecteurPosition(fichier_entree=path_actions + "\\attaqueciteor.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()

        OCR().upgrade_wall()

        # ----------------------------------------------------

        LecteurPosition(fichier_entree=path_actions + "\\switch_lucas_.json").rejouer()
        time.sleep(3)
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\selectfirstarmy.json").rejouer()
        LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        time.sleep(1)
        for i in range(3):
            LecteurPosition(fichier_entree=path_actions + "\\lose.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()
        for i in range(15):
            LecteurPosition(fichier_entree=path_actions + "\\attaque_lucas_.json").rejouer()
            time.sleep(3)
            LecteurPosition(fichier_entree=path_actions + "\\cliclefttop.json").rejouer()

        OCR().upgrade_wall()

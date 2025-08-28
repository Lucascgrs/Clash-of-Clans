import time
from datetime import datetime
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController
import json
import winsound

class EnregistreurPosition:
    def __init__(self, fichier_sortie="attaqueptitlulu.json"):
        self.actions = []
        self.fichier_sortie = fichier_sortie
        self.enregistrement_en_cours = False
        self.temps_debut = 0
        self.souris = MouseController()  # Contrôleur de souris pour obtenir la position

    def on_move(self, x, y):
        if self.enregistrement_en_cours:
            temps_actuel = time.time() - self.temps_debut
            self.actions.append({
                'type': 'mouvement_souris',
                'x': x,            # Utilise directement les coordonnées de l'événement
                'y': y,
                'temps': temps_actuel
            })

    def on_click(self, x, y, button, pressed):
        if self.enregistrement_en_cours:
            temps_actuel = time.time() - self.temps_debut
            self.actions.append({
                'type': 'clic_souris',
                'x': x,            # Utilise directement les coordonnées de l'événement
                'y': y,
                'bouton': str(button),
                'presse': pressed,
                'temps': temps_actuel
            })

    def on_scroll(self, x, y, dx, dy):
        if self.enregistrement_en_cours:
            temps_actuel = time.time() - self.temps_debut
            self.actions.append({
                'type': 'defilement_souris',
                'x': x,            # Utilise directement les coordonnées de l'événement
                'y': y,
                'dx': dx,
                'dy': dy,
                'temps': temps_actuel
            })

    def on_press(self, key):
        if self.enregistrement_en_cours:
            temps_actuel = time.time() - self.temps_debut
            try:
                touche = key.char
            except AttributeError:
                touche = str(key)

            self.actions.append({
                'type': 'pression_touche',
                'touche': touche,
                'temps': temps_actuel
            })

        # Arrêter l'enregistrement avec Échap
        try:
            if key == keyboard.Key.esc:
                self.arreter_enregistrement()
                return False
        except:
            pass

    def on_release(self, key):
        if self.enregistrement_en_cours:
            temps_actuel = time.time() - self.temps_debut
            try:
                touche = key.char
            except AttributeError:
                touche = str(key)

            self.actions.append({
                'type': 'relachement_touche',
                'touche': touche,
                'temps': temps_actuel
            })

    def demarrer_enregistrement(self):
        print("Enregistrement des actions démarré...")
        print("Appuyez sur ESC pour terminer l'enregistrement.")

        winsound.Beep(1000, 200)  # bip à 1000 Hz pendant 200 ms

        self.actions = []
        self.temps_debut = time.time()
        self.enregistrement_en_cours = True

        # Enregistrer la position initiale de la souris
        x_initial, y_initial = self.souris.position
        self.actions.append({
            'type': 'position_initiale',
            'x': x_initial,
            'y': y_initial,
            'temps': 0.0
        })

        # Démarrer les listeners
        self.listener_souris = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener_clavier = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )

        self.listener_souris.start()
        self.listener_clavier.start()

        # Attendre que l'utilisateur termine l'enregistrement
        self.listener_clavier.join()

    def arreter_enregistrement(self):
        if self.enregistrement_en_cours:
            self.enregistrement_en_cours = False

            # Ajouter des métadonnées
            metadata = {
                'date_enregistrement': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'nombre_actions': len(self.actions),
                'duree_totale': time.time() - self.temps_debut
            }

            donnees = {
                'metadata': metadata,
                'actions': self.actions[:-1]
            }

            # Enregistrer les données
            with open(self.fichier_sortie, 'w') as f:
                json.dump(donnees, f, indent=2)

            print(f"Enregistrement terminé. {len(self.actions)} actions enregistrées.")
            print(f"Données sauvegardées dans '{self.fichier_sortie}'")


if __name__ == "__main__":
    time.sleep(3)
    enregistreur = EnregistreurPosition(fichier_sortie="C:\\Users\\lucas\\PycharmProjects\\PROJECT\\Clash Of Clans\\Actions\\infoouvriersuivant.json")
    enregistreur.demarrer_enregistrement()
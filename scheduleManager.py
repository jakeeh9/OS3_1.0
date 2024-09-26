import csv
import shutil
import os


class Schedule:
    def __init__(self):
        self.list = []


    def copyFile(self, source):
        destination = os.getcwd()
        try:
            self.filePath = shutil.copy(source, destination)
            return True
        except FileNotFoundError:
            print("Could not find schedule to copy")
            return False
        except:
            return False



    def open(self, filename):
        print("Opening", filename)
        tempList = []
        try:
            with open(filename, 'r') as scheduleFile:
                fileRow = csv.reader(scheduleFile)
                for row in fileRow:
                    tempList.append(row)
        except FileNotFoundError:
            print("Error: Schedule file not found.")
            return False
        except:
            print("Error opening schedule file.")
            return False


        # Now check the schedule is OK
        #validFormat = True
        if tempList[0][0] != "Sat Name":
            validFormat = False
            print("Error: Invalid Schedule Format (Sat Name)")
        elif tempList[0][1] != "Catalog No":
            validFormat = False
            print("Error: Invalid Schedule Format (Catalog No)")
        elif tempList[0][10] != "Culmination AZ (deg)":
            validFormat = False
            print("Error: Invalid Schedule Format (Culmination Az (deg))")
        elif tempList[0][11] != "Culmination EL (deg)":
            validFormat = False
            print("Error: Invalid Schedule Format (Culmination EL (deg))")
        elif tempList[0][13] != "Culmination Date":
            validFormat = False
            print("Error: Invalid Schedule Format (Culmination Date)")
        else:
            validFormat = True

        if validFormat:
            # Copy only the relevant information into the list to keep
            self.list.append(["Name", "Catalog Number", "Azimuth", "Elevation", "Time"])
            for row in tempList[1:]:
                self.list.append([row[0], row[1], row[10], row[11], row[13]])
            return True
        else:
            return False
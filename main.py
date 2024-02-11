#!/bin/env python3
import datetime
import functools
import inspect
import sqlite3
import sys
import time
from tkinter import font

import bcrypt
import pymsgbox

import logging as logg
import driver
import printer
import tk

logg.logProcesses = logg.logThreads = logg.logMultiprocessing = False

logg.basicConfig(
    filename="debug.log",
    filemode="a",
    format="%(asctime)s:%(levelname)s:%(funcName)s:%(message)s",
    level=logg.DEBUG,
)
logging = logg.getLogger()
streamer = logg.StreamHandler()
streamer.setLevel(logg.ERROR)
logging.addHandler(streamer)
logger = logg.FileHandler("log.log")
logger.setFormatter(
    logg.Formatter("%(asctime)s:%(levelname)s:%(funcName)s:%(message)s")
)
logger.setLevel(logg.WARNING)
logging.addHandler(logger)


if "--test-run" in sys.argv:
    logging.debug("Printing Test")
    try:
        printer.printlate("hello world")
    except FileNotFoundError:
        print("Printer Not Found")
    except IOError:
        logging.critical("Weird exception. Race condition might have occured.")
    exit(0)

DEBUG = True
window = tk.Tk()
helv = lambda x: functools.partial(font.Font, weight="bold", family="Helvetica")(size=x)
helv36 = helv(36)


def sqldata(command: str, *replace, database="data.db", fetch=0):
    logging.debug(f'Running sql command "{command}"')
    try:
        CONN = sqlite3.connect(database)
        CURSOR = CONN.cursor()
        if not fetch:
            output = CURSOR.execute(command, replace)
        elif fetch == 1:
            output = CURSOR.execute(command, replace).fetchone()
        else:
            output = CURSOR.execute(command, replace).fetchall()
        CURSOR.close()
        CONN.commit()
        CONN.close()
        return output
    except Exception as e:  # Um... there was an error. Eh, itll be fine
        # pymsgbox.alert("There was an internal error.\nSome data may be lost.")
        logging.error(f"Exception executing SQL: {e}")
        raise sqlite3.Error(e)


logging.debug("Geting admin info")
try:
    ADMINS = {
        i[1]: i[2]
        for i in sqldata("""SELECT Name, Username, PasswordHash FROM Admins""", fetch=2)
    }
except sqlite3.Error as e:
    pymsgbox.alert(
        "There was an error getting admin info.\nThe program will still work, but the admin console will "
        "be disabled.",
        "ERROR",
    )
    ADMINS = {}
    logging.critical("Admin data not found")
else:
    logging.debug(f"Admin Info: {ADMINS}")


def getReadableTime():
    """Gets the current time in a human-readable format"""
    return datetime.datetime.now().strftime("%I:%M:%S %p")


def getReadableDate():
    return datetime.datetime.now().strftime("%m/%d/%Y")


def printLateSlip(name: str):
    """Prints out a late slip using a kiosk printer"""
    logging.info(f"Printing late slip for {name}")
    try:
        printer.printlate(name)
    except FileNotFoundError:
        logging.critical("Printer Not found")
        pymsgbox.alert("Printer error, please talk to Ms.Linda for a late Slip")
    except IOError:
        logging.critical("Weird exception. Race condition might have occured.")


def validateName(win: tk.Toplevel, FnameEntry: tk.Entry, LnameEntry: tk.Entry):
    Fname = FnameEntry.get().capitalize()
    Lname = LnameEntry.get().capitalize()
    logging.debug(f"Validating Name {Fname} {Lname}")
    if not (len(Fname) > 0 or len(Lname) > 0):
        (
            errLbl := tk.Label(
                win, background="red", text="You must enter both firstname and lastname"
            )
        ).pack()
        errLbl["font"] = helv(12)
        logging.info(f"Name validation failed for {Fname} {Lname}")
    else:
        logging.debug(f"Adding visitor {Fname} {Lname}")
        try:
            sqldata(
                f"""INSERT INTO Visitors (FirstName, LastName, TimeIn, DateIn) VALUES (?, ?, ? , ?)""",
                Fname,
                Lname,
                getReadableTime(),
                getReadableDate(),
            )
        except sqlite3.Error as e:
            logging.critical(f"Failed to add visitor {Fname} {Lname}")
        try:
            printer.printvisitor(f"{Fname} {Lname}")
        except FileNotFoundError:
            logging.critical(f"Printer not found")
            pymsgbox.alert(
                "There was an error with the printer. Please talk to Ms. Linda"
            )
        except IOError:
            logging.critical("Weird exception. Race condition might have occured.")
        else:
            pymsgbox.alert(
                "You are successfully signed in!\n Remember to sign out again later",
                "Success",
                timeout=10000,
            )
        win.destroy()


def StudentValidate(
    grades: tk.IntVar, win: tk.Toplevel, FName: tk.Entry, LName: tk.Entry, SignIn: bool
):
    fname = FName.get().capitalize()
    lname = LName.get().capitalize()
    logging.debug(f"Validating student {fname} {lname}")
    if not (fname and lname):
        logging.info(f"{fname} {lname} failed to validate")
        tk.Label(
            win,
            background="red",
            text="You must enter both firstname and lastname",
            font=helv(12),
        ).grid(columnspan=8)
        return
    grade = grades.get()
    if not grade:
        tk.Label(
            win,
            background="red",
            text="You must select a grade",
            font=helv(12),
        ).grid(columnspan=8)
        return
    if SignIn:  # if the function is being called for a sign in.
        logging.debug(f"{fname} {lname} came in late")
        printLateSlip(f"{fname} {lname}")
        pymsgbox.alert("Here is your late slip.", timeout=10000)
        win.destroy()
        return
    logging.info(f"{fname} {lname} left early")
    return


def checkstudent(signIn: bool):
    if DEBUG:
        if signIn:
            studentSignIn()
            return
        studentSignOut()
        return
    if not (datetime.time(7) < datetime.datetime.now().time() < datetime.time(16)):
        logging.warning(
            f"Someone tried to sign {'in' if signIn else 'out'} at a weird time."
        )
        pymsgbox.alert("What are you doing at this time?")
        return
    if signIn:
        if datetime.datetime.now().time() < datetime.time(8, 30, 0, 0):
            logging.warning("Someone tried to sign in at a weird time.")
            pymsgbox.alert(
                "Um... It is earlier than 8:30, you don't need a late slip",
                "?????",
            )
            return
        if datetime.datetime.now().time() > datetime.time(3, 30):
            logging.warning(f"Someone tried to sign in at a weird time.")
            pymsgbox.alert(
                "Hm... I think it's too late for that",
                "?????",
            )
            return
        studentSignIn()
        return
    if datetime.datetime.now().time() < datetime.time(15, 15, 0, 0):
        logging.warning(f"Someone tried to sign out at a weird time.")
        pymsgbox.alert(
            "Um... It is later than 3:15, you don't need to sign out",
            "?????",
        )
        return
    if datetime.datetime.now().time() < datetime.time(8, 30):
        logging.warning(f"Someone tried to sign out at a weird time.")
        pymsgbox.alert(
            "Hm... I think it's too early for that",
            "?????",
        )
        return
    studentSignOut()
    return


def createStudentPage(title, sign_type, signIN):
    StudentPage = tk.Toplevel(bg="blue")
    StudentPage.title(title)
    StudentPage.config(width=300, height=200, bg="green")
    selgrde = tk.IntVar()
    tk.Label(StudentPage, text="Grade", font=helv(21), background="blue").grid(
        row=0, column=0, columnspan=8
    )
    grades = []
    special = {1: "st", 2: "nd", 3: "rd"}
    for i in range(12):
        curr = tk.Radiobutton(
            StudentPage,
            text=f"{i + 1}{'th' if i + 1 not in special else special[i + 1]}",
            value=i + 1,
            variable=selgrde,
        )
        grades.append(curr)
        curr.grid(row=2, column=i)
    tk.Label(StudentPage, text="First Name:", background="blue", font=helv36).grid(
        columnspan=8
    )
    (nameEntry := tk.Entry(StudentPage, font=helv36)).grid(columnspan=8)
    tk.Label(StudentPage, text="Last Name:", background="blue", font=helv36).grid(
        columnspan=8
    )
    (LnameEntry := tk.Entry(StudentPage, font=helv36)).grid(columnspan=8)
    validation_func = functools.partial(
        StudentValidate, selgrde, StudentPage, nameEntry, LnameEntry, signIN
    )
    tk.Button(
        StudentPage, text=sign_type, bg="green", command=validation_func, font=helv(21)
    ).grid(columnspan=8)
    StudentPage.focus()
    nameEntry.focus()
    StudentPage.grab_set()


def studentSignOut():
    createStudentPage("Student Sign Out", "Sign Out", False)


def studentSignIn():
    createStudentPage("Student Sign In", "Sign In", True)


def visitorinpage():
    visitorquestion = tk.Toplevel(bg="orange")
    visitorquestion.title("Visitor Sign In")
    visitorquestion.config(width=300, height=200)
    tk.Label(visitorquestion, text="First Name:", background="blue", font=helv36).pack()
    (nameEntry := tk.Entry(visitorquestion, font=helv36)).pack()
    tk.Label(visitorquestion, text="Last Name:", background="blue", font=helv36).pack()
    (LnameEntry := tk.Entry(visitorquestion, font=helv36)).pack()
    validation = functools.partial(validateName, visitorquestion, nameEntry, LnameEntry)
    tk.Button(
        visitorquestion, text="Sign In", bg="green", command=validation, font=helv(21)
    ).pack()
    visitorquestion.focus()
    nameEntry.focus()
    visitorquestion.grab_set()
    return


def processSignOut(win: tk.Toplevel, Fnamebox: tk.Entry, Lnamebox: tk.Entry):
    Fname = Fnamebox.get().capitalize()
    Lname = Lnamebox.get().capitalize()
    signedIn = sqldata("SELECT FirstName, LastName FROM Visitors", fetch=2)
    if (Fname, Lname) not in signedIn:
        logging.info(f"Visitor {Fname} {Lname} was never signed in")
        pymsgbox.alert(
            f"Visitor {Fname} {Lname} not found in database, please check your spelling",
            timeout=30000,
        )
        return
    try:
        signout(Fname, Lname)
    except sqlite3.Error as e:
        logging.error(f"Signing {Fname} {Lname} out failed: {e}")
    else:
        logging.debug(f"Visitor {Fname} {Lname} signed out")
    pymsgbox.alert("You have been successfully signed out", timeout=20000)
    win.destroy()
    return


def visitoroutpage():
    visitorquestion = tk.Toplevel(bg="orange")
    visitorquestion.title("Visitor Sign Out")
    visitorquestion.config(width=300, height=200)
    (
        nameLabel := tk.Label(visitorquestion, text="First Name:", background="blue")
    ).pack()
    (nameEntry := tk.Entry(visitorquestion)).pack()
    nameLabel["font"] = helv36
    nameEntry["font"] = helv36
    (
        LnameLabel := tk.Label(visitorquestion, text="Last Name:", background="blue")
    ).pack()
    (LnameEntry := tk.Entry(visitorquestion)).pack()
    LnameLabel["font"] = helv36
    LnameEntry["font"] = helv36
    validation = functools.partial(
        processSignOut, visitorquestion, nameEntry, LnameEntry
    )
    (
        submitName := tk.Button(
            visitorquestion, text="Sign Out", bg="green", command=validation
        )
    ).pack()
    submitName["font"] = helv(21)

    visitorquestion.focus()
    nameEntry.focus()
    visitorquestion.grab_set()
    return


def signout(fname: str, lname: str):
    TimeIn, DateIn = sqldata(
        f"""SELECT TimeIn, DateIn FROM Visitors WHERE FirstName = ? AND LastName = ?""",
        fname,
        lname,
        fetch=1,
    )
    sqldata(
        f"""DELETE FROM Visitors WHERE FirstName = ? AND LastName = ?""",
        fname,
        lname,
    )
    sqldata(
        f"""INSERT INTO PastVisitors (FirstName, LastName, TimeIn, DateIn, TimeOut, DateOut) VALUES (?, ?, ?, 
        ?, ?, ?)""",
        fname,
        lname,
        TimeIn,
        DateIn,
        getReadableTime(),
        getReadableDate(),
    )
    pymsgbox.alert(f"{fname} {lname} has been signed out", "Success")


def clearpast():
    logging.warning("Past was cleared")
    sqldata("DELETE FROM PastVisitors")


def signoutall():
    logging.warning("All were signed out")
    sqldata(f"DELETE FROM Visitors")


def addnewadmin(uname: str, pwd: str, name: str):
    logging.warning(f"Adding new admin: {name}:{uname}")
    passwordh = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
    sqldata(
        f"INSERT INTO Admins (Name, Username, PasswordHash) VALUES (?, ?, ?)",
        name,
        uname,
        passwordh,
    )
    return "", 204


def addnewadmininter():
    name = pymsgbox.prompt(
        "Enter the new admins real name:", "Admin Adder", timeout=60000
    )
    if name is None:
        return
    if name == "":
        pymsgbox.alert("Invalid name", "Error", timeout=5000)
    while True:
        username = pymsgbox.prompt(
            "Enter the new admins username:", "Admin Adder", timeout=60000
        )
        if username.lower() in ADMINS:
            pymsgbox.alert(
                "That username is taken. Please try another", "Error", timeout=30000
            )
            continue
        if name is None:
            return
        if name == "":
            resp = pymsgbox.confirm(
                "Invalid name. To cancel, press cancel",
                "Error",
                buttons=["continue", "cancel"],
            )
            if resp == "continue":
                continue
            return
        break
    while True:
        while True:
            password = pymsgbox.password(
                "Enter the new admins password:", "Admin Adder"
            )
            if password is None:
                if (
                    pymsgbox.confirm(
                        "Are you sure you want to cancel?",
                        "Are you sure",
                        buttons=["Yes", "No"],
                    )
                    == "Yes"
                ):
                    return
                continue
            if password == "":
                resp = pymsgbox.confirm(
                    "Password cannot be blank. If you are trying to cancel, press cancel",
                    "Error",
                    buttons=["cancel", "continue"],
                )
                if resp == "cancel":
                    return
                continue
            if len(password) < 4:
                if (
                    pymsgbox.confirm(
                        "Insecure password, are you sure you want to continue?",
                        "Warning",
                        buttons=["Yes, continue with an insecure password", "Go Back"],
                    )
                    == "Go Back"
                ):
                    continue
            break
        while True:
            confirmed = pymsgbox.password(
                "Enter your password one more time to confirm", "Confirm"
            )
            if confirmed == password:
                addnewadmin(username, password, name)
                pymsgbox.alert(f"New admin {name} added successfully", "Success")
                return
            if (
                pymsgbox.confirm(
                    "Passwords do not match",
                    buttons=["Confirm again", "Enter new password"],
                )
                == "Confirm again"
            ):
                continue
            break


def newViewCurrent(currentTop: tk.Toplevel | tk.Tk):
    Vis = tk.Toplevel(currentTop)
    Vis.title("Current Visitors")
    try:
        visitors = sqldata(
            "SELECT FirstName, LastName, TimeIn, DateIn FROM Visitors", fetch=2
        )
    except sqlite3.Error as e:
        Vis.destroy()
        logging.error(f"Error retreiving current visitors: {e}")
        pymsgbox.alert(
            "Error loading visitor data. Please check the logs for more info."
        )
        return
    if not visitors:
        pymsgbox.alert("There are no visitors currently")
        Vis.destroy()
        return
    heads = ["First Name", "Last Name", "Time Signed In", "Date Signed In"]
    tab = tk.Sheet(
        Vis,
        "Current Visitors",
        data=visitors,
        auto_resize_columns=50,
        auto_resize_rows=30,
        width=int((500 / 4) * len(heads)),
        height=100,  # 100 * len(visitors),
    )
    tab.enable_bindings("row_height_resize", "arrowkeys")
    tab.set_header_data(heads)
    tab.grid(rowspan=len(visitors), columnspan=1, column=0)
    cnt = 0
    for fnam, lnam, _, _ in visitors:
        tk.Button(
            Vis, text="Sign Out", command=functools.partial(signout, fnam, lnam)
        ).grid(row=cnt, column=1)
        cnt += 1


def viewPast(currentTop: tk.Toplevel | tk.Tk):
    Vis = tk.Toplevel(currentTop)
    Vis.title("Past Visitors")
    try:
        signedout = sqldata(
            "SELECT FirstName, LastName, TimeIn, DateIn, TimeOut, DateOut FROM PastVisitors",
            fetch=2,
        )
    except sqlite3.Error as e:
        Vis.destroy()
        logging.error(f"Error retreiving past visitors: {e}")
        pymsgbox.alert(
            "Error loading visitor data. Please check the logs for more info."
        )
        return
    heads = [
        "First Name",
        "Last Name",
        "Time Signed In",
        "Date Signed In",
        "Time Signed Out",
        "Date Signed Out",
    ]
    tab = tk.Sheet(
        Vis,
        "Past Visitors",
        data=signedout,
        auto_resize_columns=50,
        auto_resize_rows=30,
        width=int((500 / 4) * len(heads)),
        height=100,  # 100 * len(signedout),
        row_height=5,
    )
    tab.enable_bindings(
        "row_height_resize",
        "arrowkeys",
        "column_height_resize",
        "row_width_resize",
        "column_width_resize",
    )
    tab.set_header_data(heads)
    tab.grid(rowspan=len(signedout))


def prepPrinter():
    prepCommands = (
        printer.INITALIZE + b"\x1c\x2e"  # Disable Chinese mode
        b"\x1B\x61\x01"  # Center align text
        + printer.SET_SIZE  # Prep set size
        + driver.binComm(0b00000001)  # Set text to double size
    )
    try:
        driver.printIfConnected(prepCommands)
    except FileNotFoundError:
        logging.critical("Printer not found for prep. Checking debug mode")
        if not DEBUG:
            logging.critical("Not in debug mode, raising exception.")
            raise
        logging.warning("In debug mode, continuing anyway")
    except IOError:
        logging.critical("Weird exception. Race condition might have occured.")


def testPrinter():
    testCommand = b"\x1d\x28\x41\02\00\x00\x64"
    try:
        driver.printIfConnected(testCommand)
    except FileNotFoundError:
        logging.critical("Printer not found for test.")
        pymsgbox.alert("Printer not found", "ERROR")
        return
    except IOError:
        logging.critical("Weird exception. Race condition might have occured.")
    time.sleep(10)
    prepPrinter()


def customPrint():
    toPrint = pymsgbox.prompt("Text to print")
    toPrint = toPrint.replace("\\n", "\n")
    try:
        printer.simplePrint(toPrint)
    except FileNotFoundError:
        logging.critical("Printer not found")
    except IOError:
        logging.critical("Weird exception. Race condition might have occured.")


# noinspection SpellCheckingInspection
def RUNadminconsole():
    logging.info("Starting admin console")
    adminconsole = tk.Toplevel()
    view = functools.partial(newViewCurrent, adminconsole)
    viewpas = functools.partial(viewPast, adminconsole)
    adminconsole.title("Admin Console")
    adminconsole.config(width=300, height=200)
    tk.Button(
        adminconsole,
        text="Add New Admin",
        bg="green",
        command=addnewadmininter,
        font=helv(21),
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(
        adminconsole,
        text="View Current Visitors",
        bg="orange",
        command=view,
        font=helv(21),
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(
        adminconsole,
        text="View Past Visitors",
        bg="blue",
        font=helv(21),
        command=viewpas,
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(
        adminconsole,
        text="Test Printer",
        bg="red",
        font=helv(21),
        command=testPrinter,
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(
        adminconsole,
        text="Custom Print",
        bg="VioletRed3",
        font=helv(21),
        command=customPrint,
    ).pack(fill=tk.BOTH, expand=True)
    adminconsole.focus()
    adminconsole.grab_set()
    return


# noinspection SpellCheckingInspection
def passenter():
    username = pymsgbox.prompt("Username:", "IDENTIFY YOURSELF", timeout=60000)
    if not username:
        return
    username = username.lower()
    if not (
        pashash := pymsgbox.password("Password", "IDENTIFY YOURSELF", timeout=60000)
    ):
        return
    if username in ADMINS:
        if bcrypt.checkpw(pashash.encode(), ADMINS[username].encode()):
            logging.info(f"Admin {username} logged in")
            RUNadminconsole()
            return
        else:
            pymsgbox.alert("Incorrect Password", "ERROR")
            return
    else:
        pymsgbox.alert("User Not Found", "ERROR")
        return


# noinspection SpellCheckingInspection
def main():
    if not DEBUG:
        window.attributes("-fullscreen", True)
    checkIN = functools.partial(checkstudent, True)
    checkOUT = functools.partial(checkstudent, False)
    tk.Button(
        text="Student Sign In\n(Late Slip)", bg="red", command=checkIN, font=helv36
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(text="Student Sign Out", bg="orange", command=checkOUT, font=helv36).pack(
        fill=tk.BOTH, expand=True
    )
    tk.Button(
        text="Visitor Sign In", bg="green", command=visitorinpage, font=helv36
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(
        text="Visitor Sign Out", bg="blue", command=visitoroutpage, font=helv36
    ).pack(fill=tk.BOTH, expand=True)
    tk.Button(
        text="Admin Console",
        bg="white",
        command=(RUNadminconsole if DEBUG else passenter),
    ).pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    if driver.isPrinterConnected():
        try:
            prepPrinter()
        except FileNotFoundError:
            while True:
                pymsgbox.alert("Printer is not found, please talk to Ms.Linda")
        main()
        window.mainloop()
    elif DEBUG:
        logging.warning("No printer found but debug mode is on, continuing anyway")
        pymsgbox.alert("No Printer Found but debug mode is on\nContinuing anyway")
        main()
        window.mainloop()
    else:
        logging.critical("Printer not found")
        while True:
            pymsgbox.alert("Printer is not found, please talk to Ms.Linda")

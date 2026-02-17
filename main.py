import os
import ctypes
import hashlib
import zlib
from datetime import datetime, timezone

def createGit():
    directory = f"{os.curdir}/.xgit"
    if not os.path.isdir(directory):
        os.mkdir(directory)
        print(f" - Directory created at {directory}")
        if os.name == 'nt':
            ctypes.windll.kernel32.SetFileAttributesW(directory, 0x02)
    return

def blobFile(f):
    data = f.read()
    header = f"1 {len(data)}\0".encode('utf-8')
    dataType = 0 #Initialise one Byte for file type
    dataType = 2 if os.access(f.name, os.X_OK) else 1 #Set to 2 if its executable else set to 1
    finalHash = compressSave(header, data)
    return (dataType, finalHash, f.name) #Returns data needed for a tree

def createIgnoreFile():
    ignoreList = [".xgit", ".git"] #Default ignored files
    with open(f"{os.curdir}/.xgit/ignore.dat", 'w') as f: f.write('\n'.join(ignoreList))
    return ignoreList

def makeTrees(directory):
    blobs = list()
    with os.scandir(directory) as files:
        for file in files:
            if file.is_file() and not file.name in ignoreList:
                with open(file, 'rb') as fileObj:
                    blobs.append(blobFile(fileObj))
            elif file.is_dir() and not file.name in ignoreList:
                blobs.append(makeTrees(file.path))
    finalTree = list()
    for x in blobs:
        finalTree.append(" ".join(map(str, x)))
    finalTreeConcat = ("\x00".join((finalTree))).encode("utf-8")
    header = f"2 {len(finalTreeConcat)}\0".encode("utf-8")
    finalHash = compressSave(header, finalTreeConcat)
    try:
        fileName = directory.rsplit("\\", 1)[1]
    except: #Parent directory
        fileName = "."
    return (10, finalHash, fileName) #Returns data needed for a tree to link to a new tree

def compressSave(header, finalBlob):
    finalData = zlib.compress(header + finalBlob)
    finalHash = hashlib.sha1(finalData).hexdigest()
    os.makedirs(f"{os.curdir}/.xgit/{finalHash[:2]}", exist_ok=True)
    if not os.path.exists(f"{os.curdir}/.xgit/{finalHash[:2]}/{finalHash}"):
        with open(f"{os.curdir}/.xgit/{finalHash[:2]}/{finalHash}", 'wb') as treeData: treeData.write(finalData)
    return finalHash

#WIP
def makeCommit(treeHash, author, comment):
    previousCommit = "" if checkLatestCommit() == None else checkLatestCommit()
    data = " ".join([previousCommit, treeHash, author, datetime.now(timezone.utc).strftime("%d/%m/%y %H:%M+00:00"), comment]).encode("utf-8")
    header = f"3 {len(data)}\0".encode("utf-8")
    commitHash = compressSave(header, data)
    with open(f"{os.curdir}/.xgit/cache", "wb") as f: f.write(commitHash.encode("utf-8"))

def checkLatestCommit():
    if not os.path.exists(f"{os.curdir}/.xgit/cache"):
        commits = list()
        if not os.path.exists(f"{os.curdir}/.xgit"):
            return #First commit
        with os.scandir(f"{os.curdir}/.xgit/") as folders:
            for files in folders:
                if files.is_dir():
                    for f in os.scandir(files): #Checking the contents of each hash folder
                        with open(f, "rb") as d:
                            data = zlib.decompress(d.read()).split(b"\0") #Decompress and split into header [0] and data [1]
                            if data[0][0] == ord("3"): #Checking if the type is commit by checking the first byte
                                commits.append({f.name : data[1].decode("utf-8").partition(" ")[0]}) #Decode the data and seperate the previous hash from the data then return the Commits Hash : Previous Commits Hash
        if len(commits) == 0:
            return #Initial commit
        return orderCommitList(commits)[0] #Return most recent commit in the list
    with open(f"{os.curdir}/.xgit/cache", "rb") as f:
        data = f.read().decode("utf-8")
    if len(data) == 40:
        print("true")
        return data
    else:
        print(" - Cache has been modified or corrupted. Regenerating")
        os.remove(f"{os.curdir}/.xgit/cache")
        return checkLatestCommit()

def orderCommitList(commits): #WIP Needs error checking still
    finalOrder = list()
    currentHash = str()
    for d in commits[:]:
        if "" == list(d.values())[0]:
            currentHash = list(d.keys())[0]
            finalOrder.append(currentHash)
            commits.remove(d)
            break

    while len(commits) > 0:
        for d in commits[:]:
            if currentHash == list(d.values())[0]:
                currentHash = list(d.keys())[0]
                finalOrder.insert(0, currentHash)
                commits.remove(d)
                break
    return(finalOrder)




createGit()
ignoreList = list()
try:
    with open(f"{os.curdir}/.xgit/ignore.dat", 'r') as f: ignoreList = f.read().split("\n")
except OSError:
    print(" - Regenerating ignore.dat")
    ignoreList = createIgnoreFile()

makeCommit(makeTrees(os.curdir)[1], 'x', 'Test Commit')



#DATA LIST:
#FILE TYPES:
#1 = File
#2 = EXE
#10 = Folder

#COMPRESSED FILE TYPES:
#1 = BLOB
#2 = TREE
#3 = COMMIT
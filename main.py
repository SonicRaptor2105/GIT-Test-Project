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
    print(dataType)
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
                print(f"file {file.name}")
                with open(file, 'rb') as fileObj:
                    blobs.append(blobFile(fileObj))
            elif file.is_dir() and not file.name in ignoreList:
                print(f"folder {file.name}")
                blobs.append(makeTrees(file.path))
    finalTree = list()
    for x in blobs:
        finalTree.append(" ".join(map(str, x)))
    finalTreeConcat = ("\x00".join((finalTree))).encode("utf-8")
    header = f"2 {len(finalTreeConcat)}\0".encode("utf-8")
    finalHash = compressSave(header, finalTreeConcat)
    print(finalTreeConcat.decode("utf-8"))
    try:
        fileName = directory.rsplit("\\", 1)[1]
        print(fileName)
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
    previousCommit = "str()"
    data = " ".join([previousCommit, treeHash, author, datetime.now(timezone.utc).strftime("%d/%m/%y %H:%M+00:00"), comment]).encode("utf-8")
    header = f"3 {len(data)}\0".encode("utf-8")
    compressSave(header, data)

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
                            print(data)
                            if data[0][0] == ord("3"):
                                commits.append(data[1].decode("utf-8").partition(" ")[0])
                                print(commits)




createGit()
ignoreList = list()
try:
    with open(f"{os.curdir}/.xgit/ignore.dat", 'r') as f: ignoreList = f.read().split("\n")
    print(ignoreList)
except OSError:
    print(" - Regenerating ignore.dat")
    ignoreList = createIgnoreFile()

makeCommit('abc', 'x', 'Test Commit')
checkLatestCommit()
#makeTrees(os.curdir)



#DATA LIST:
#FILE TYPES:
#1 = File
#2 = EXE
#10 = Folder

#COMPRESSED FILE TYPES:
#1 = BLOB
#2 = TREE
#3 = COMMIT
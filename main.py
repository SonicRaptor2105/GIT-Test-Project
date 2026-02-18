import os
import ctypes
import hashlib
import zlib
from datetime import datetime, timezone

def createGit(dir):
    directory = f"{dir}/.xgit"
    if not os.path.isdir(directory):
        os.mkdir(directory)
        print(f" - Directory created at {directory}")
        if os.name == 'nt':
            ctypes.windll.kernel32.SetFileAttributesW(directory, 0x02) #Marks the folder as hidden on windows
    return

def blobFile(dir, f):
    data = f.read()
    header = f"1 {len(data)}\0".encode('utf-8') #Creates header of file type (1 for BLOB) and length of data stored
    dataType = 0
    dataType = 2 if os.access(f.name, os.X_OK) else 1 #Set to 2 if its executable else set to 1
    finalHash = compressSave(dir, header, data)
    return (dataType, finalHash, os.path.basename(f.name)) #Returns data needed for a tree

def createIgnoreFile(dir):
    try:
        with open(f"{dir}/.xgit/ignore.dat", 'r') as f: ignoreList = f.read().split("\n") #Check if the ignore.dat file exists
    except OSError:
        print(" - Regenerating ignore.dat")
    ignoreList = [".xgit", ".git"] #Default ignored files
    with open(f"{dir}/.xgit/ignore.dat", 'w') as f: f.write('\n'.join(ignoreList))
    return ignoreList

def makeTrees(directory):
    blobs = list()
    with os.scandir(directory) as files: #Scan all folders and subfolders in a directory and save that snapshot as BLOBs and TREEs
        for file in files:
            if file.is_file() and not file.name in ignoreList:
                with open(file, 'rb') as fileObj:
                    blobs.append(blobFile(directory, fileObj))
            elif file.is_dir() and not file.name in ignoreList:
                blobs.append(makeTrees(file.path))
    finalTree = list()
    for x in blobs:
        finalTree.append(" ".join(map(str, x)))
    finalTreeConcat = ("\x00".join((finalTree))).encode("utf-8")
    header = f"2 {len(finalTreeConcat)}\0".encode("utf-8")
    finalHash = compressSave(directory, header, finalTreeConcat)
    try:
        fileName = directory.rsplit("\\", 1)[1]
    except: #Parent directory
        fileName = "."
    return (10, finalHash, fileName) #Returns data needed for a tree to link to a new tree

def compressSave(dir, header, finalBlob):
    finalData = zlib.compress(header + finalBlob) #Compress the header and data into 1 compressed file
    finalHash = hashlib.sha1(finalData).hexdigest() #Take the hash of the compressed contents
    os.makedirs(f"{dir}/.xgit/{finalHash[:2]}", exist_ok=True) #Make a directory with the first 2 characters of the hash
    if not os.path.exists(f"{dir}/.xgit/{finalHash[:2]}/{finalHash}"):
        with open(f"{dir}/.xgit/{finalHash[:2]}/{finalHash}", 'wb') as treeData: treeData.write(finalData)
    return finalHash #Returs the hash which is used for file linking in TREEs and COMMITs

#WIP
def makeCommit(dir, treeHash, author, comment):
    while " " in author:
        author = author.replace(" ", "_") #Ensuring no spaces in the authors name
    previousCommit = "" if checkLatestCommit(dir) == None else checkLatestCommit(dir) #Check if this is the first commit or if not what the previous commit hash was
    data = " ".join([previousCommit, treeHash, author, datetime.now(timezone.utc).strftime("%d/%m/%y-%H:%M+00:00"), comment]).encode("utf-8")
    header = f"3 {len(data)}\0".encode("utf-8")
    commitHash = compressSave(dir, header, data)
    with open(f"{dir}/.xgit/cache", "wb") as f: f.write(commitHash.encode("utf-8")) #Create cache if it doesn't exist and record the hash of the latest commit to save time finding it in the future

def checkLatestCommit(dir):
    if not os.path.exists(f"{dir}/.xgit/cache"): #First check if the cache exists and use that before attempting to find the latest commit by reading files
        commits = list()
        if not os.path.exists(f"{dir}/.xgit"):
            return #First commit
        with os.scandir(f"{dir}/.xgit/") as folders:
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
    with open(f"{dir}/.xgit/cache", "rb") as f:
        data = f.read().decode("utf-8")
    if len(data) == 40:
        return data
    else: #If the hash is invalid reject it and find it using the above method
        print(" - Cache has been modified or corrupted")
        os.remove(f"{dir}/.xgit/cache") #Delete the cache so it isn't checked again until it is recreated with the next commit
        return checkLatestCommit(dir) #Rerun without checking cache

def orderCommitList(commits): #WIP Needs error checking still
    finalOrder = list()
    currentHash = str()
    for d in commits[:]:
        if "" == list(d.values())[0]: #Find the very first commit
            currentHash = list(d.keys())[0]
            finalOrder.append(currentHash)
            commits.remove(d) #Remove from the list
            break

    while len(commits) > 0: #Continue until all commits have been sorted
        for d in commits[:]:
            if currentHash == list(d.values())[0]: #If the current hash is equal to the prior hash then the selected hash becomes the current hash
                currentHash = list(d.keys())[0]
                finalOrder.insert(0, currentHash)
                commits.remove(d)
                break
    return(finalOrder) #Returns a list of hashes that correlate to commit files, in order of newest to oldest

def splitContent(dir, hash):
    with open(f"{dir}/.xgit/{hash[:2]}/{hash}", "rb") as f: d = f.read()
    header, rawData = (zlib.decompress(d)).split(b"\0", 1) #Split the file into header and data
    return header.decode('utf-8'), rawData #Return both header and content. Content is not decoded here incase it is a non utf-8 file like a .png

def readCommit(dir, commit):
    path = f"{dir}/.xgit/{commit[:2]}/{commit}"
    if os.path.exists(path):
        _, rawData = splitContent(dir, commit) #Take the data and ignore the header
        keys = ["PreviousCommitHash", "TreeHash", "Author", "DateTime", "Comment"]
        data = rawData.decode("utf-8").split(" ", 4)
        commitUnpacked = dict(zip(keys, data)) #Pack the data into a more human readable dict form
        return(commitUnpacked)
    return

def unpackTree(dir, treeHash, folderName = None):
    _, treeData = splitContent(dir, treeHash) #Take only the tree content and ignore the header
    treeData = [s.split(" ") for s in treeData.decode("utf-8").split("\x00")] #rawData is now a 2d list in the structure [[dataType, fileHash, fileName], ...]
    print(treeData)
    for file in treeData:
        if file[0] == '10': #If the instance is a folder
            unpackTree(dir, file[1], f"{f"{folderName}/" if folderName != None else ""}{file[2]}") #Unpack the subfolder if it exists while accounting for already being in a subfolder
        else:
            os.makedirs(f"{dir}/.xgit/TEST{f"/{folderName}" if folderName != None else ""}", exist_ok=True)
            if file != [""]: #If theres data in the folder create it otherwise skip
                _, blobData = splitContent(dir, file[1]) #Take only the blob contnet and leave the header
                with open(f"{dir}/.xgit/TEST/{f"{folderName}/" if folderName != None else ""}{file[2]}", "wb") as f: f.write(blobData)





if __name__ == "__main__":
    while True:
        path = input("Path to parent directory: ")
        if os.path.exists(path):
            break
        print(" - Path is invalid")
    createGit(path)
    ignoreList = createIgnoreFile(path)
    makeCommit(path, makeTrees(path)[1], 'x', 'Super Cool Test Commit')
    unpackTree(path, readCommit(path, checkLatestCommit(path))["TreeHash"])


#DATA LIST:
#FILE TYPES:
#1 = File
#2 = EXE
#10 = Folder

#COMPRESSED FILE TYPES:
#1 = BLOB
#2 = TREE
#3 = COMMIT
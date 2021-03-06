import scipy
import scipy.sparse.csgraph as csgraph
import scipy.sparse
import matplotlib.pyplot as plt
import itertools
import numpy as np

def get_shortestPath(graph,start,end):
    sdist, pred = csgraph.shortest_path(graph, directed=False, indices = (start,end), return_predecessors=True)
    path=[]
    prev = end
    path.append(end)
    while prev != start:
        prev = pred[0][prev]
        path.append(prev)
    return path

def get_pathDist(graph,path):
    dist = 0
    for step in zip(path, path[1:]):
        dist += graph.todok()[step[0],step[1]]
    return dist

def highlight_cell(x,y, ax=None, **kwargs):
    rect = plt.Rectangle((x-.5, y-.5), 1,1, fill=False, **kwargs)
    ax = ax or plt.gca()
    ax.add_patch(rect)
    return rect

def get_uumat_ravel_cell(rcell,umatshape,uumatshape,mapping):
    """
    From a ravel cell of the umat obtain the correspinding ravel cell of the uumat
    umatshape and uumatshape are 2D list
    """
    cell = np.unravel_index(rcell,umatshape)
    unf_cell = mapping[cell]
    unf_cell = np.asarray(list(unf_cell))
    unf_rcell = np.ravel_multi_index(unf_cell.T,uumatshape)
    return unf_rcell

def get_cells_copies(shape,cell):
    i,j = cell
    n1,n2 = shape
    cells = [(i-n1,j-n2),(i-n1,j),(i-n1,j+n2),(i,j-n2),(i,j),(i,j+n2),(i+n1,j-n2),(i+n1,j),(i+n1,j+n2)]
    return cells

def remove_uumat_offset(uumat,mapping,reversed_mapping):
    n1,n2 = uumat.shape

    #Computing uumat offset
    row_offset, col_offset = [0,0], [0,0]
    row_break, col_break = [True,True], [True,True]
    for i in range(n1):
        row = uumat[i]
        col = uumat[:,i]
        rowinf = np.isinf(row).astype(int)
        colinf = np.isinf(col).astype(int)
        if (sum(rowinf) == n1) and (row_break[0] == True):
            row_offset[0]+=1
        else:
            row_break[0] = False
        if (sum(colinf) == n2) and (col_break[0] == True):
            col_offset[0]+=1
        else:
            col_break[0] = False
    for i in range(n1-1,-1,-1):
        row = uumat[i]
        col = uumat[:,i]
        rowinf = np.isinf(row).astype(int)
        colinf = np.isinf(col).astype(int)
        if (sum(rowinf) == n1) and (row_break[1] == True):
            row_offset[1]+=1
        else:
            row_break[1] = False
        if (sum(colinf) == n2) and (col_break[1] == True):
            col_offset[1]+=1
        else:
            col_break[1] = False 

    #Applying uumat offset to the uumat,mapping and reversed_mapping
    uumat = uumat[row_offset[0]:, :]
    uumat = uumat[:-row_offset[1], :]
    uumat = uumat[:,col_offset[0]:]
    uumat = uumat[:,:-col_offset[1],]
    for k in mapping:
        mapping[k] = tuple(np.asarray(mapping[k]) - [row_offset[0],col_offset[0]])
    new_reversed_mapping = {}
    for k in reversed_mapping:
        newk = tuple(np.asarray(k) - [row_offset[0],col_offset[0]])
        new_reversed_mapping[newk] = reversed_mapping[k]
    reversed_mapping = new_reversed_mapping
    
    return uumat, mapping, reversed_mapping


def get_unfold_umat(umat,adj,qbmus,mstree,offset=True):
    """
    Unfold a U-Matrix (umat) using a minimal spanning tree (mstree) between BMUS (bmus)
    """
    #Parse the inital data
    n1, n2 = umat.shape
    qbmus = np.asarray(list(set(qbmus)))
    qbmus_ravel = np.ravel_multi_index(qbmus.T,(n1,n2))
    mstree_pairs = np.asarray(list(mstree.nonzero()))
    mstree_data = mstree.data

    #Initalize the outpu. The new unfold umat (uumat) will be generated by 
    #extending the umat on each of the 8 possible directions.
    mapping = {}
    reversed_mapping = {}
    uumat = np.ones((n1*3,n2*3))*np.inf

    #Reorder mstree_pairs and mstree_data dinamicaly to start from the closest pair of qbmus
    dmstree_pairs = [[],[]]
    dmstree_data = []
    mstree_len = len(mstree_data)
    for i in range(mstree_len):
        if i == 0:
            minindx = np.argmin(mstree_data)
        else:
            explored_indx = np.squeeze(dmstree_pairs)
            indxs0 = np.in1d(mstree_pairs[0], explored_indx).nonzero()[0]
            indxs1 = np.in1d(mstree_pairs[1], explored_indx).nonzero()[0]
            indxs = np.concatenate((indxs0,indxs1))
            minaux = np.inf
            for indx in indxs:
                if mstree_data[indx] < minaux:
                    minaux = mstree_data[indx]
                    minindx = indx
        dmstree_data.append(mstree_data[minindx])
        dmstree_pairs[0].append(mstree_pairs[0][minindx])
        dmstree_pairs[1].append(mstree_pairs[1][minindx])
        mstree_data = np.delete(mstree_data,minindx)
        mstree_pairs = np.delete(mstree_pairs,minindx,axis=1)
        
    #Start by relocating the queries
    for c1,c2 in zip(*dmstree_pairs):
        i1, j1 = np.unravel_index(c1,(n1,n2))
        i2, j2 = np.unravel_index(c2,(n1,n2))
        #To avoid moving twice a single query
        if (i2,j2) in mapping:
            iaux, jaux = i2,j2
            i2, j2 = i1, j1
            i1 ,j1 = iaux, jaux
        if (i1,j1) in mapping:
            _i1,_j1 = mapping[(i1,j1)]
        else:
            mapping[(i1, j1)] = tuple((i1, j1)+np.asarray([n1,n2]))
            reversed_mapping[tuple((i1, j1)+np.asarray([n1,n2]))] = (i1, j1)
            _i1, _j1 = mapping[(i1, j1)]
        _i2, _j2 = i2+n1, j2+n2
        cells = get_cells_copies((n1,n2),(_i2,_j2))
        cells = np.asarray(cells)
        dists = np.linalg.norm(cells-np.asarray([_i1,_j1]),axis=1)
        minindx = dists.argmin()
        unfindx = tuple(cells[minindx])
        uumat[unfindx] = umat[i2,j2]
        mapping[(i2,j2)] = unfindx
        reversed_mapping[unfindx] = (i2,j2)

    #Now move the rest of cells
    qbmus_ravel = np.ravel_multi_index(np.asarray(list(mapping.keys())).T, (n1, n2))
    sdist, pred = csgraph.shortest_path(adj, indices = qbmus_ravel, directed=False, return_predecessors=True)
    qbmus = np.asarray(list(mapping.values()))
    closest_qbmus = qbmus[sdist.argmin(axis=0)]
    indx = 0
    for i in range(n1):
        for j in range(n2):
            _i, _j = i+n1,j+n2
            cells = get_cells_copies((n1,n2),(_i,_j))
            cells = np.asarray(cells)
            closest_qbmu = closest_qbmus[indx]
            dists = np.linalg.norm(cells-closest_qbmu,axis=1)
            minindx = dists.argmin()
            unfindx = tuple(cells[minindx])
            uumat[unfindx] = umat[i,j]
            mapping[(i,j)] = unfindx
            reversed_mapping[unfindx]=(i,j)
            indx += 1
    
    if offset:
        uumat, mapping, reversed_mapping = remove_uumat_offset(uumat,mapping,reversed_mapping)

    return uumat, mapping, reversed_mapping  

def get_localadjmat(umat,adjmat,bmus,verbose=True):
    #Get all paths and path distances for all combinations of queries and generate a new graph of shortest distances between queries

    n1,n2 = umat.shape
    indxbmus = [np.ravel_multi_index(bmu,(n1,n2)) for bmu in bmus]

    localadj= {'data': [], 'row': [], 'col': []}
    paths = {}
    checkpairs = []
    indxbmus = list(set(indxbmus))
    size = int((len(list(itertools.permutations(indxbmus, 2))))/2)
    count = 0
    for pair in itertools.permutations(indxbmus, 2):
        if pair not in checkpairs and (pair[1],pair[0]) not in checkpairs:
            checkpairs.append(pair)
        else:
            continue
        count += 1
        if verbose:
            print(str(count) + "/" + str(size))
        localadj['row'].extend([pair[0],pair[1]])
        localadj['col'].extend([pair[1],pair[0]])
        if verbose:
            print('Computing shortest path between: %d %d'%(pair[0],pair[1]))
        path = get_shortestPath(adjmat,pair[0], pair[1])
        paths[pair] = path
        paths[(pair[1],pair[0])] = path
        if verbose:
            print('Computing the lenght of the shortest path between: %d %d'%(pair[0],pair[1]))
        pathDist = get_pathDist(adjmat,path)
        localadj['data'].extend([pathDist,pathDist])
    localadj = scipy.sparse.coo_matrix((localadj['data'], (localadj['row'], localadj['col'])))
    return localadj,paths

def load_localadjmat(localadjmat):
    localadj = scipy.sparse.load_npz(localadjmat)
    return localadj

def get_minsptree(localadj,paths,verbose=True):
    mstree = csgraph.minimum_spanning_tree(localadj)
    mstree_pairs = np.asarray(mstree.nonzero())
    mstree_pairs = np.vstack((mstree_pairs[0], mstree_pairs[1])).T
    return mstree_pairs,paths

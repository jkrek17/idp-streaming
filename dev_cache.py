import pickle, os, idp_ratings as M, offense as O
def get():
    if os.path.exists("off_cache.pkl"):
        return pickle.load(open("off_cache.pkl","rb"))
    D = M.load_data(M.nfl.get_current_season()); B = O.build(D)
    pickle.dump((D,B), open("off_cache.pkl","wb")); return D,B

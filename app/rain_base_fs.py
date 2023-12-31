"""Functions to write Rainfields netcdf radar data to MongoDB 

    Returns:
        MongoDB __id__ on success else returns None  
"""
import os
import gridfs
from pymongo import MongoClient
from netCDF4 import Dataset
from datetime import datetime

# function to read the nc file and get the metadata


def get_metadata(buf):
    """_summary_extract metadata from the nc file

    Args:
        buf (_type_): buffer with the netCDF file

    Returns:
        Dictionary: {
            "variable": Name of the variable,
            "station_id": Rainfields station id,
            "station_name": Rainfields station name,
            "valid_time": Valid time for the field,
            "start_time": Start time for the field,
            "mean": mean,
            "std": standard deviation,
            "war": wetted area ratio
            }
    """
    ncFile = Dataset("fname", mode="r", memory=buf)
    var_list = ncFile.variables.keys()

    my_metadata = {}
    # my_metadata["station_id"] = int(ncFile.__getattr__("station_id"))
    # my_metadata["station_name"] = str(ncFile.__getattr__("station_name"))
    # my_metadata['valid_time'] = int(ncFile['valid_time'][0].item())
    my_metadata["station_id"] = str(ncFile.__getattr__("site_code"))
    my_metadata["station_name"] = str(ncFile.__getattr__("site_name"))
    scan_time_dt = datetime.strptime(ncFile.scan_time, '%Y-%m-%d %H:%M:%S')
    my_metadata['start_time'] = int(scan_time_dt.strftime('%Y%m%d%H%M%S'))

    # if 'start_time' in var_list:
    #     my_metadata['start_time'] = int(ncFile['start_time'][0].item())

    # get the type of rainfall variable
    my_variable = None
    if 'precipitation' in var_list:
        my_variable = 'precipitation'
    if 'rain_rate' in var_list:
        my_variable = 'rain_rate'
    if 'HSR' in var_list:
        my_variable='HSR'

    if my_variable is not None:
        my_metadata['variable'] = my_variable
    else:
        print("Valid rainfall variable not found")
        print(f"{var_list=}")
        return None

    # calculate the stats for this field
    rain = ncFile[my_variable][:]
    my_metadata["mean"] = rain.mean()
    my_metadata["std"] = rain.std()
    rain_area = (rain >= 0.05).sum()
    valid_area = rain.count()
    my_metadata["war"] = rain_area / valid_area

    return my_metadata


def write_to_rain_basefs(**kwargs):
    """Write a rainfields3 netcdf file of rainfall to the mongodb
    kwargs:
        file_path: the full path to the rainfields3 netcdf file 
        db_client: the mongodb client

    Returns:
        mongdo db id on sucess, else None
    """
    db_client = kwargs.get("db_client", None)
    if db_client is None:
        print("Error: Missing db_client kwarg")
        return None

    rf3_name = kwargs.get("file_path", None)
    if rf3_name is None:
        print("Error: Missing file_path kwarg")
        return None

    # read the ncfile into memory
    try:
        nc_file = open(rf3_name, "rb")
        buf = nc_file.read()
        nc_file.close()
    except FileNotFoundError:
        print(f"Error: {rf3_name} not found")
        return None

    # get the metadata
    fname = os.path.basename(rf3_name)
    my_metadata = get_metadata(buf)

    # get the product from the file name and add it to the metadata 
    # fname_list = fname.split(".")
    # my_metadata["product"] = fname_list[-2]
    my_metadata["product"] ="Z_HSR_00_033"
    fs = gridfs.GridFSBucket(db_client)
    file_id = fs.upload_from_stream(fname, buf, metadata=my_metadata)

    return file_id

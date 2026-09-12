; Exact spherical Albers export matching backend/geometry.py.
; Kept separate so the long projection string is stored only once.
direct_radar_projection {
    sub append() {
        direct_radar.append(iso:"%7B%22wkt%22%3A%22PROJCS%5B%5C%22WC%5C%22%2CGEOGCS%5B%5C%22Sphere%5C%22%2CDATUM%5B%5C%22D%5C%22%2CSPHEROID%5B%5C%22S%5C%22%2C6371000%2C0%5D%5D%2CPRIMEM%5B%5C%22Greenwich%5C%22%2C0%5D%2CUNIT%5B%5C%22De")
        direct_radar.append(iso:"gree%5C%22%2C0.0174532925199433%5D%5D%2CPROJECTION%5B%5C%22Albers%5C%22%5D%2CPARAMETER%5B%5C%22False_Easting%5C%22%2C0%5D%2CPARAMETER%5B%5C%22False_Northing%5C%22%2C0%5D%2CPARAMETER%5B%5C%22Central_Me")
        direct_radar.append(iso:"ridian%5C%22%2C-96%5D%2CPARAMETER%5B%5C%22Standard_Parallel_1%5C%22%2C29.5%5D%2CPARAMETER%5B%5C%22Standard_Parallel_2%5C%22%2C45.5%5D%2CPARAMETER%5B%5C%22Latitude_Of_Origin%5C%22%2C0%5D%2CUNIT%5B%5C%2")
        direct_radar.append(iso:"2Meter%5C%22%2C1%5D%5D%22%7D")
    }
}

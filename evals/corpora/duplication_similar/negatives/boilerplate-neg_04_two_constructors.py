# why: negative - two N-field constructors for genuinely different value objects; same arity but each sets distinct attributes on a distinct type, so they should not collapse to one helper.
def make_geo_point(latitude, longitude, altitude, accuracy, source):
    point = GeoPoint()
    point.lat = latitude
    point.lon = longitude
    point.alt = altitude
    point.accuracy_m = accuracy
    point.source = source
    return point


def make_colour_sample(red, green, blue, alpha, label):
    colour = ColourSample()
    colour.r = red
    colour.g = green
    colour.b = blue
    colour.a = alpha
    colour.label = label
    return colour

# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
from flask import (Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    abort
)
from flask_migrate import Migrate
from flask_moment import Moment
from flask_wtf import Form
from sqlalchemy import func
from logging import Formatter, FileHandler
from forms import *
from models import *
import dateutil.parser
import babel
import logging
import config
import sys


# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#
app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#
def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


def countUpcomingShows(shows):
    num_upcoming_shows = 0
    for show in shows:
        if show.start_time > datetime.now():
            num_upcoming_shows += 1
    return num_upcoming_shows


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#
@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():
    places = Venue.query.distinct(Venue.city, Venue.state).all()
    venues = Venue.query.all()

    data = []
    for place in places:
        temp_venues = {
            'city': place.city,
            'state': place.state,
            'venues': []
        }

        for venue in venues:
            if venue.city == place.city and venue.state == place.state:
                num_upcoming_shows = countUpcomingShows(venue.shows)
                temp_venues['venues'].append({
                    'id': venue.id,
                    'name': venue.name,
                    'num_upcoming_shows': num_upcoming_shows
                })

        data.append(temp_venues)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_text = request.form['search_term']
    venues = Venue.query.filter(Venue.name.ilike(f'%{search_text}%')).all()

    data = []
    for venue in venues:
        num_upcoming_shows = countUpcomingShows(venue.shows)
        data.append({
            'id': venue.id,
            'name': venue.name,
            'num_upcoming_shows': num_upcoming_shows
        })

    response = {
        "count": len(venues),
        "data": data
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    print(venue.genres)
    if not venue:
        abort(400)

    queried_past_shows = venue.shows.join(Artist, Artist.id == Show.artist_id)\
        .filter(Show.start_time <= func.now())\
        .with_entities(Show.artist_id,
                       Artist.name.label('artist_name'),
                       Artist.image_link.label('artist_image_link'),
                       Show.start_time)\
        .all()
    past_shows = []
    for show in queried_past_shows:
        past_shows.append({
            'artist_id': show.artist_id,
            'artist_name': show.artist_name,
            'artist_image_link': show.artist_image_link,
            'start_time': str(show.start_time)
        })

    queried_upcoming_shows = venue.shows.join(Artist, Artist.id == Show.artist_id)\
        .filter(Show.start_time > func.now())\
        .with_entities(Show.artist_id,
                       Artist.name.label('artist_name'),
                       Artist.image_link.label('artist_image_link'),
                       Show.start_time)\
        .all()
    upcoming_shows = []
    for show in queried_upcoming_shows:
        upcoming_shows.append({
            'artist_id': show.artist_id,
            'artist_name': show.artist_name,
            'artist_image_link': show.artist_image_link,
            'start_time': str(show.start_time)
        })

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # Set the FlaskForm
    form = VenueForm(request.form, meta={'csrf': False})

    # Validate all fields
    if form.validate():
        error = False
        try:
            venue = Venue(name=form.name.data, 
                          city=form.city.data, 
                          state=form.state.data, 
                          address=form.address.data, 
                          phone=form.phone.data, 
                          genres=form.genres.data, 
                          facebook_link=form.facebook_link.data,
                          image_link=form.image_link.data, 
                          website_link=form.website_link.data, 
                          seeking_talent=form.seeking_talent.data, 
                          seeking_description=form.seeking_description.data
            )
            db.session.add(venue)
            db.session.commit()
        except:
            print(sys.exc_info())
            error = True
            db.session.rollback()
        finally:
            db.session.close()

        if error:
            flash('An error occurred. Venue ' +
                form.name.data + ' could not be listed.')
        else:
            flash('Venue ' + form.name.data + ' was successfully listed!')

        return render_template('pages/home.html')
    # If there is any invalid field
    else:
        message = []
        for field, errors in form.errors.items():
            for error in errors:
                message.append(f"{field}: {error}")
        flash('Please fix the following errors: ' + ', '.join(message))
        form = VenueForm()
        return render_template('forms/new_venue.html', form=form)

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue:
        abort(404)

    error = False
    try:
        db.session.delete(venue)
        db.session.commit()
    except:
        print(sys.exc_info())
        error = True
        db.session.rollback()
    finally:
        db.session.close()

    if error:
        abort(500)
    return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.with_entities(Artist.id, Artist.name).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_text = request.form['search_term']
    artists = Artist.query.filter(Artist.name.ilike(f'%{search_text}%'))\
                    .with_entities(Artist.id, Artist.name)\
                    .all()
    response = {
        "count": len(artists),
        "data": artists
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist:
        abort(404)

    queried_past_shows = artist.shows.join(Venue, Venue.id == Show.venue_id)\
        .filter(Show.start_time <= func.now())\
        .with_entities(Show.venue_id,
                       Venue.name.label('venue_name'),
                       Venue.image_link.label(
                           'venue_image_link'),
                       Show.start_time)\
        .all()
    past_shows = []
    for show in queried_past_shows:
        past_shows.append({
            'venue_id': show.venue_id,
            'venue_name': show.venue_name,
            'venue_image_link': show.venue_image_link,
            'start_time': str(show.start_time)
        })

    queried_upcoming_shows = artist.shows.join(Venue, Venue.id == Show.venue_id)\
        .filter(Show.start_time > func.now())\
        .with_entities(Show.venue_id,
                       Venue.name.label('venue_name'),
                       Venue.image_link.label(
                           'venue_image_link'),
                       Show.start_time)\
        .all()
    upcoming_shows = []
    for show in queried_upcoming_shows:
        upcoming_shows.append({
            'venue_id': show.venue_id,
            'venue_name': show.venue_name,
            'venue_image_link': show.venue_image_link,
            'start_time': str(show.start_time)
        })

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist:
        abort(404)
    form = ArtistForm(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist:
        abort(404)

    form = ArtistForm(request.form, meta={'csrf': False})
    error = False

    try:
        artist.name = form.name.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        artist.genres = form.genres.data
        artist.image_link = form.image_link.data
        artist.facebook_link = form.facebook_link.data
        artist.website_link = form.website_link.data
        artist.seeking_venue = form.seeking_venue.data
        artist.seeking_description = form.seeking_description.data
        db.session.commit()
    except:
        error = True
        print(sys.exc_info())
        db.session.rollback()
    finally:
        db.session.close()

    if error:
        abort(500)

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue:
        abort(404)
    form = VenueForm(obj=venue)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue:
        abort(404)

    form = VenueForm(request.form, meta={'csrf': False})
    error = False

    try:
        venue.name = form.name.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        venue.image_link = form.image_link.data
        venue.facebook_link = form.facebook_link.data
        venue.genres = form.genres.data
        venue.website_link = form.website_link.data
        venue.seeking_description = form.seeking_description.data
        venue.seeking_talent = form.seeking_talent.data
        db.session.commit()
    except:
        error = True
        print(sys.exc_info())
        db.session.rollback()
    finally:
        db.session.close()

    if error:
        abort(500)

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form, meta={'csrf': False})

    if form.validate():
        error = False
        try:
            artist = Artist(name=form.name.data,
                            city=form.city.data,
                            state=form.state.data,
                            phone=form.phone.data,
                            genres=form.genres.data,
                            image_link=form.image_link.data,
                            facebook_link=form.facebook_link.data,
                            website_link=form.website_link.data,
                            seeking_venue=form.seeking_venue.data,
                            seeking_description=form.seeking_description.data)
            db.session.add(artist)
            db.session.commit()
        except:
            print(sys.exc_info())
            error = True
            db.session.rollback()
        finally:
            db.session.close()

        if error:
            flash('An error occurred. Artist ' +
                form['name'] + ' could not be listed.')
        else:
            flash('Artist ' + form['name'] + ' was successfully listed!')

        return render_template('pages/home.html')
    else:
        message = []
        for field, errors in form.errors.items():
            for error in errors:
                message.append(f"{field}: {error}")
        flash('Please fix the following errors: ' + ', '.join(message))
        form = ArtistForm()
        return render_template('forms/new_artist.html', form=form)


#  Shows
#  ----------------------------------------------------------------
@app.route('/shows')
def shows():
    shows = Show.query.join(Venue, Venue.id == Show.venue_id)\
        .join(Artist, Artist.id == Show.artist_id)\
        .with_entities(Show.venue_id, Venue.name.label('venue_name'),
                       Show.artist_id, Artist.name.label('artist_name'),
                       Artist.image_link.label('artist_image_link'), Show.start_time)\
        .order_by(Show.start_time.asc())\
        .all()

    data = []
    for show in shows:
        data.append({
            'venue_id': show.venue_id,
            'venue_name': show.venue_name,
            'artist_id': show.artist_id,
            'artist_name': show.artist_name,
            'artist_image_link': show.artist_image_link,
            'start_time': str(show.start_time)
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form, meta={'csrf': False})

    if form.validate():
        venue_id = form.venue_id.data
        artist_id = form.artist_id.data
        start_time = form.start_time.data

        error = False
        try:
            show = Show(venue_id=venue_id, artist_id=artist_id,
                        start_time=start_time)
            db.session.add(show)
            db.session.commit()
        except:
            print(sys.exc_info())
            error = True
            db.session.rollback()
        finally:
            db.session.close()

        if error:
            flash('An error occurred. Show could not be listed.')
        else:
            flash('Show was successfully listed!')

        return render_template('pages/home.html')
    else:
        message = []
        for field, errors in form.errors.items():
            for error in errors:
                message.append(f"{field}: {error}")
        flash('Please fix the following errors: ' + ', '.join(message))
        form = ShowForm()
        return render_template('forms/new_show.html', form=form)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

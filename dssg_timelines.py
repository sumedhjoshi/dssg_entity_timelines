# Module for creating timeline visualizations.
import psycopg2
import sys
import matplotlib.pyplot as plt
import pandas as pd

def get_timeline_data( pg_credentials, entity_id, schema_name, table_names, date_column, description_column=[], masks=[]  ):
	""" Constructs a query to build a month-by-month timeline for a given entity ID with events from several tables """

	# Cast the entity id to a string.
	entity_id = str(entity_id)

	# If the masks list is empty, initialize it to a list of empty strings.
	if len(masks) == 0:
		masks = [""] * len(table_names) 

	# Connect to the database.
	conn_string = "host="+ pg_credentials.PGHOST +  \
				  " port="+ "5432" + \
				  " dbname="+ pg_credentials.PGDATABASE + \
				  " user=" + pg_credentials.PGUSER  + \
				  " password="+ pg_credentials.PGPASSWORD 
	conn = psycopg2.connect(conn_string)

	# Create a cursor obejct.
	cursor = conn.cursor()

	# Build flags to describe event types from the first three letters of the table names.
	flag = { table: table for table in table_names }
	
	# Get mask strings to use in SQL queries.
	maskstr = get_sql_masks( table_names, masks )

	# Create the SQL query string.
	query = ''
	for table in table_names:
		tablestr = schema_name + '.' +  table
		datestr  = "date_trunc( 'month', " + tablestr + '.' + date_column[table] + ")"
		if len( description_column ) > 0:
			descstr  = 'cast( ' + tablestr + '.' + description_column[table] + ' as varchar)'
		this_query = 'SELECT ' + datestr + ' AS date, ' + descstr + ' AS desc, ' + "'" + flag[table] + "'" + ' AS type ' + 'FROM ' + tablestr + ' WHERE ' + tablestr + '.anonid = ' + str(entity_id) + maskstr[table] + '\n'
		if len(query) > 0:
			query = query + 'UNION \n' + this_query
		else:
			query = query + this_query
	        
	# Order by date.
	query = query + 'ORDER BY date, type ASC'
	
	# Execute the query.
	cursor.execute( query )
	timeline = pd.DataFrame( cursor.fetchall(), columns=['date','description','type'])

	# Sort the data by month and type.
	timeline['monthcount'] = 1
	count = 1
	for index, row in timeline.iterrows():
		if index > 0:
			this_row_month = timeline['date'].ix[index]
			last_row_month = timeline['date'].ix[index-1]
			last_row_count = timeline['monthcount'].ix[index-1]
        
        	# If the months didn't change, increment the month counter.
			if this_row_month == last_row_month:
				timeline.ix[index,'monthcount'] = last_row_count + 1

	# Return the timeline data.
	return timeline, query

def create_timeline_plot( timeline, color_dict, shape_dict, titlestr="", fig_height=16, fig_width=20, year_limits=[2011,2016], marker_size=75.0 ):
	""" Creates a timeline graphic given an entity ID and a timeline as generated by get_timeline_data() """ 

	# Extract the data for plotting.
	x_data      = timeline['date']
	y_data      = timeline['monthcount']
	type_data   = timeline['type']
	
	# Get a list of unique types in the timeline data.
	unique_types = list( type_data.unique() )
	
	# Create a figure and time-axis.
	fig, ax = plt.subplots(figsize=(fig_width,fig_height))
	ax.hold(True)

	# For each event type, create a scatter plot.
	for event_type in unique_types:
		
		# Get the x and y values.i
		mask = timeline['type'] == event_type
		data = timeline[mask]
		x_data = data['date']
		y_data = data['monthcount']

		# For light colors, make the edges darker.
		if color_dict[event_type] in ["yellow","white","pink"]:
			linewidth = 1.5
		else:
			linewidth = 0.0

		# Create the scatter plot.
		ax.scatter(x_data.values, y_data.values, 
			marker=shape_dict[event_type], s=marker_size, c=color_dict[event_type], linewidths=linewidth, edgecolors='k' )
	
	# Make the figure pretty.
	fig.autofmt_xdate()
	ax.yaxis.set_visible(False)
	ax.spines['right'].set_visible(False)
	ax.spines['left'].set_visible(False)
	ax.spines['top'].set_visible(False)
	ax.xaxis.set_ticks_position('bottom')
	ax.set_axis_bgcolor('whitesmoke')
	plt.xticks(rotation=80)
	plt.tick_params(labelsize=20)
	
	# Set the title.
	plt.title( titlestr, fontsize=20)
	
	# Set the x-axis limits and labels.
	year_min = pd.to_datetime(str( year_limits[0] ) )
	year_max = pd.to_datetime(str(year_limits[1]))
	month    = pd.to_timedelta(1, unit='M')
	six_months = pd.to_timedelta(6,unit='M')
	plt.xlim(year_min - month ,year_max + six_months)
	plt.ylim(0.5,)

	# Show the plot.
	plt.show()

	# Return the axis handle.
	return ax

def get_sql_masks( tables, masks ):
	""" Turns SQL-like mask statements into strings to be used in SQL queries """
	
	# Pre-pend with AND where necessary.
	maskstring = list()
	for ndx, table in enumerate(tables):
		if len(masks[ndx]) > 0:
			maskstring.append( " AND " + masks[ndx] )
		else:
			maskstring.append("")

	# Turn these lists into a dictionary.
	return dict( zip( tables, maskstring ) )

from migrate.versioning.shell import main
from dragon.db.sqlalchemy import migrate_repo
import os

import ConfigParser

config = ConfigParser.SafeConfigParser()
config.readfp(open('/etc/dragon/dragon.conf'))
sql_connection = config.get('DEFAULT', 'sql_connection')

if __name__ == '__main__':
    main(debug='False',
         url=sql_connection,
         repository=os.path.abspath(os.path.dirname(migrate_repo.__file__)))

import {Injectable, Injector} from '@angular/core';
import {Tweet} from '../../_models/Tweet';
import {AbstractDataManager} from '../data-manager/data-manager.abstract';
import {MapModes} from '../../_models/MapModes';

@Injectable()
export class EdinburghDataManagerService extends AbstractDataManager {

  constructor(injector: Injector) {
    super(injector);

    this.dataFile = 'edinburgh-wards.json';
    this.topologyId = 'WD13CD';
    this.topologyName = 'WD13NM';
    this.mapType = 'edinburgh';
    this.regionName = 'Edinburgh';
    this.districtId = 'S12000036';
    this.mapMode = MapModes.Edinburgh;
    this.allowRegionPulsing = true;
    this.apiDataRoute = 'all_scotland_ward_data';

    this.loadDistrictsData();

    this.listenOnSockets();
  }

  protected listenOnSockets(): void {
    this._tweet.getScotlandDistrictTweets().subscribe((msg: Tweet) => this.updateLastTweet(msg, msg.ward));
    this._tweet.getScotlandWardTweets().subscribe((msg: Tweet) => this.updateLastTweet(msg, msg.ward));
  }
}

import {Injectable, Injector} from '@angular/core';
import {AbstractDataManager} from '../data-manager/data-manager.abstract';
import {Tweet} from '../../_models/Tweet';

@Injectable()
export class GlasgowDataManagerService extends AbstractDataManager {

  constructor(injector: Injector) {
    super(injector);

    this.dataFile = 'glasgow-wards.json';
    this.topologyId = 'WD13CD';
    this.topologyName = 'WD13NM';
    this.mapType = 'glasgow';
    this.regionName = 'Glasgow';
    this.districtId = 'S12000046';

    this.loadDistrictsData();

    this.listenOnSockets();
  }

  protected getDistrictsData(ids: string[]) {
    return this._http.get<any>('/api/all_scotland_ward_data', {
      params: {ids, region: 'true'}
    });
  }

  protected listenOnSockets(): void {
    this._tweet.scotland_district_tweets.subscribe((msg: Tweet) => this.updateLastTweet(msg, msg.ward));
    this._tweet.scotland_ward_tweets.subscribe((msg: Tweet) => this.updateLastTweet(msg, msg.ward));
  }
}
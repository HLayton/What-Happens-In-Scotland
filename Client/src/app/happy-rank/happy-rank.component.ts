import {
  Component, Input, OnChanges, OnInit, SimpleChanges, ViewEncapsulation
} from '@angular/core';
import {DataManagerService} from '../_services';
import {District} from '../_models/District';

/**
 * Component to generate and display a bar chart that shows how happiness ranks between wards
 */
@Component({
  selector: 'app-happy-rank',
  templateUrl: './happy-rank.component.html',
  styleUrls: [
    './happy-rank.component.css',
    // include original nvd3 styles
    '../../../node_modules/nvd3/build/nv.d3.css'
  ],
  encapsulation: ViewEncapsulation.None
})
export class HappyRankComponent implements OnInit, OnChanges {

  @Input() ward: District;
  @Input() wards: {[id: string]: District};

  public barOptions: any;
  public barData: any[];

  constructor(private _dataManager: DataManagerService) { }

  public ngOnInit(): void {
    this.setOptions();
  }

  /**
   * Reacts to any changes to the @Input variables
   * @param {SimpleChanges} changes
   */
  public ngOnChanges(changes: SimpleChanges): void {
    if (changes['ward']) {
      this.setData();
    }
  }

  /**
   * Sets the options for the happy rank bar chart
   */
  private setOptions(): void {
    this.barOptions = {
      chart: {
        discretebar: {
          dispatch: {
            elementClick: e => this._dataManager.setDistrict(e.data.id)

          }
        },
        useInteractiveGuideline: true,
        type: 'discreteBarChart',
        yDomain: [-1, 1],
        height: 250,
        margin : {
          top: 20,
          right: 20,
          bottom: 50,
          left: 55
        },
        x: d => d.label,
        y: d => d.value,
        showValues: true,
        valueFormat: d => d.toFixed(1),
        duration: 500,
        xAxis: {
          axisLabel: 'Wards (Ranked)',
          tickFormat: (d, i) => (i === 0 || i === 20) ? d : ''
        },
        yAxis: {
          axisLabel: 'Happiness',
          axisLabelDistance: -10
        }
      }
    };
  }

  /**
   * Sets the data for the happy rank bar chart
   */
  private setData(): void {
    const barData = [
      {
        key: 'Wards',
        values: []
      }
    ];
    if (this.wards !== undefined) {
      for (const [key, ward] of Object.entries(this.wards)) {
        if ('average' in ward) {
          // Line chart data should be sent as an array of series objects.
          barData[0].values.push(
            {
              value: ward.average,
              id: key,
              label: ward.name,
              color: (this.ward === ward) ? '#7cff6c' : (key === this._dataManager.getMapBoundaryId()) ? '#48BFFF' : '#b8b9ac'
            }
          );
        }
      }
    }

    barData[0].values.sort((a, b) => b.value - a.value);
    this.barData = barData;
  }

}
